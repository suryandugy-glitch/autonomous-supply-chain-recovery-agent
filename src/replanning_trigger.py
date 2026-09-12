"""
Replanning Trigger for the Autonomous Supply Chain Recovery Agent
Monitors for conditions that invalidate current plan and initiates goal re-assessment and replanning cycle
"""

import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .config import config
from .state_manager import state_manager
from .goal_manager import goal_manager
from .disruption_detector import disruption_detector
from .utils import setup_logging

# Setup logger
logger = setup_logging(__name__)

class ReplanningTrigger:
    """Triggers replanning when conditions change or current plan becomes invalid"""

    def __init__(self):
        self._replanning_thread = None
        self._stop_replanning = threading.Event()
        self._last_replanning_check = {}
        self._replanning_history = []
        self._plan_validity_cache = {}

        # Replanning intervals
        self.replanning_interval = config.get_agent_param('monitoring_interval') or 30

        # Thresholds for triggering replanning
        self.replanning_thresholds = {
            'objective_degradation': 0.3,  # 30% degradation in objective progress triggers replanning
            'new_severe_disruption': True,  # Any new severe disruption triggers replanning
            'plan_obsolete_time': 1800,    # 30 minutes without valid plan triggers replanning
            'failed_action_threshold': 2,   # 2 consecutive failed actions triggers replanning
            'major_state_change': 0.4       # 40% change in state variables triggers replanning
        }

    def start_replanning_monitoring(self) -> None:
        """Start the replanning monitoring thread"""
        if self._replanning_thread is not None and self._replanning_thread.is_alive():
            logger.warning("Replanning trigger is already running")
            return

        logger.info("Starting replanning trigger...")
        self._stop_replanning.clear()
        self._replanning_thread = threading.Thread(target=self._replanning_loop, daemon=True)
        self._replanning_thread.start()

    def stop_replanning_monitoring(self) -> None:
        """Stop the replanning monitoring thread"""
        logger.info("Stopping replanning trigger...")
        self._stop_replanning.set()
        if self._replanning_thread:
            self._replanning_thread.join(timeout=5.0)

    def _replanning_loop(self) -> None:
        """Main replanning monitoring loop"""
        logger.info("Replanning loop started")

        while not self._stop_replanning.is_set():
            try:
                self._check_replanning_conditions()
                time.sleep(self.replanning_interval)
            except Exception as e:
                logger.error(f"Error in replanning loop: {e}")
                time.sleep(5)  # Short sleep on error

        logger.info("Replanning loop stopped")

    def _check_replanning_conditions(self) -> None:
        """Check if any conditions warrant triggering replanning"""
        try:
            # Check 1: Objective degradation
            if self._check_objective_degradation():
                self._trigger_replanning("Objective degradation detected")
                return

            # Check 2: New severe disruptions
            if self._check_new_severe_disruptions():
                self._trigger_replanning("New severe disruption detected")
                return

            # Check 3: Plan obsolescence (time-based)
            if self._check_plan_obsolescence():
                self._trigger_replanning("Plan has become obsolete due to time")
                return

            # Check 4: Consecutive failed actions
            if self._check_consecutive_failed_actions():
                self._trigger_replanning("Multiple consecutive failed actions")
                return

            # Check 5: Major state changes
            if self._check_major_state_changes():
                self._trigger_replanning("Major state changes detected")
                return

        except Exception as e:
            logger.error(f"Error checking replanning conditions: {e}")

    def _check_objective_degradation(self) -> bool:
        """Check if any objectives have degraded significantly"""
        try:
            # Get current objective progress
            overall_progress = goal_manager.get_overall_goal_progress()

            if not overall_progress or overall_progress.get('total_objectives', 0) == 0:
                return False

            # Check each objective for significant degradation
            objective_details = overall_progress.get('objective_details', {})
            for obj_key, obj_progress in objective_details.items():
                current_progress = obj_progress.get('progress_percentage', 0.0)
                is_met = obj_progress.get('is_met', False)
                trend = obj_progress.get('trend', 'stable')

                # If objective was met but now has significantly degraded
                if is_met and current_progress < (100 - self.replanning_thresholds['objective_degradation']):
                    logger.info(f"Objective {obj_key} degraded from met to {current_progress}%")
                    return True

                # If objective is declining rapidly
                if trend == 'declining' and current_progress < 50.0:
                    logger.info(f"Objective {obj_key} is declining rapidly at {current_progress}%")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking objective degradation: {e}")
            return False

    def _check_new_severe_disruptions(self) -> bool:
        """Check for new severe disruptions that weren't present in last check"""
        try:
            # Get recent disruptions
            recent_disruptions = state_manager.get_recent_disruptions(limit=20)

            # Check for severe disruptions that are recent
            current_time = time.time()
            recent_severe_disruptions = []

            for disruption in recent_disruptions:
                # Check if it's severe
                if disruption.get('severity') == 'high':
                    # Check if it's recent (within last 2 replanning intervals)
                    disruption_time = datetime.fromisoformat(disruption.get('timestamp', datetime.now().isoformat()))
                    time_diff = (datetime.now() - disruption_time).total_seconds()

                    if time_diff < (self.replanning_interval * 2):
                        recent_severe_disruptions.append(disruption)

            # If we found new severe disruptions since last check
            last_severe_check = self._last_replanning_check.get('severe_disruption_time', 0)
            if recent_severe_disruptions:
                latest_disruption_time = max(
                    datetime.fromisoformat(d.get('timestamp', datetime.now().isoformat())).timestamp()
                    for d in recent_severe_disruptions
                )

                if latest_disruption_time > last_severe_check:
                    self._last_replanning_check['severe_disruption_time'] = latest_disruption_time
                    logger.info(f"Found {len(recent_severe_disruptions)} new severe disruptions")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking for new severe disruptions: {e}")
            return False

    def _check_plan_obsolescence(self) -> bool:
        """Check if the current plan has become obsolete due to time"""
        try:
            # Check when we last did meaningful replanning
            last_replan_time = self._last_replanning_check.get('last_replan_time', 0)
            if last_replan_time == 0:
                # Never replanned, check if we have any actions at all
                recent_actions = state_manager.get_recent_actions(limit=5)
                if len(recent_actions) == 0:
                    # No actions ever taken - might need to start
                    return False
                else:
                    # We have taken actions, so we should replan periodically
                    last_action_time = max(
                        datetime.fromisoformat(a.get('timestamp', datetime.now().isoformat())).timestamp()
                        for a in recent_actions
                    )
                    last_replan_time = last_action_time

            time_since_last_replan = time.time() - last_replan_time
            max_time_without_replan = self.replanning_thresholds['plan_obsolete_time']

            if time_since_last_replan > max_time_without_replan:
                logger.info(f"Plan has been obsolete for {time_since_last_replan/60:.1f} minutes")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking plan obsolescence: {e}")
            return False

    def _check_consecutive_failed_actions(self) -> bool:
        """Check for consecutive failed actions that suggest current approach isn't working"""
        try:
            # Get recent actions
            recent_actions = state_manager.get_recent_actions(limit=10)

            if len(recent_actions) < self.replanning_thresholds['failed_action_threshold']:
                return False  # Not enough actions to judge

            # Check the last N actions for failures
            failed_count = 0
            for action in recent_actions[-self.replanning_thresholds['failed_action_threshold']:]:
                action_type = action.get('action_type', '')
                # Consider an action failed if it's explicitly marked as failed
                if 'failed' in action_type or action.get('execution_result', {}).get('status') == 'failed':
                    failed_count += 1

            if failed_count >= self.replanning_thresholds['failed_action_threshold']:
                logger.info(f"Found {failed_count} consecutive failed actions")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking consecutive failed actions: {e}")
            return False

    def _check_major_state_changes(self) -> bool:
        """Check for major changes in state variables that invalidate current assumptions"""
        try:
            # Get current state summary
            current_state = state_manager.get_state_summary()

            # Get last known state for comparison
            last_state = self._last_replanning_check.get('last_state_summary')
            if not last_state:
                # First time checking, store current state and return False
                self._last_replanning_check['last_state_summary'] = current_state
                return False

            # Calculate changes in key state variables
            changes = {}
            total_change = 0.0
            count = 0

            # Compare key metrics
            key_metrics = ['inventory_items', 'active_shipments', 'vendors_tracked', 'demand_forecasts']

            for metric in key_metrics:
                current_val = current_state.get(metric, 0)
                last_val = last_state.get(metric, 0)

                if last_val != 0:
                    change_pct = abs(current_val - last_val) / last_val
                else:
                    change_pct = 1.0 if current_val > 0 else 0.0

                changes[metric] = change_pct
                total_change += change_pct
                count += 1

            # Also check for significant changes in disruption patterns
            recent_disruptions = state_manager.get_recent_disruptions(limit=10)
            disruption_types = [d.get('type') for d in recent_disruptions]
            last_disruption_types = last_state.get('recent_disruption_types', [])

            # Simple comparison of disruption type diversity
            current_types_set = set(disruption_types)
            last_types_set = set(last_disruption_types)
            if last_types_set:
                type_change = len(current_types_set.symmetric_difference(last_types_set)) / len(last_types_set.union(current_types_set))
            else:
                type_change = 1.0 if len(current_types_set) > 0 else 0.0

            changes['disruption_diversity'] = type_change
            total_change += type_change
            count += 1

            average_change = total_change / count if count > 0 else 0.0

            # If average change exceeds threshold, trigger replanning
            if average_change > self.replanning_thresholds['major_state_change']:
                logger.info(f"Major state changes detected: {changes}")
                self._last_replanning_check['last_state_summary'] = current_state
                self._last_replanning_check['last_state_change_time'] = time.time()
                return True
            else:
                # Update last state if no major change
                self._last_replanning_check['last_state_summary'] = current_state

            return False

        except Exception as e:
            logger.error(f"Error checking major state changes: {e}")
            return False

    def _trigger_replanning(self, reason: str) -> None:
        """Trigger a replanning cycle"""
        try:
            logger.warning(f"Triggering replanning: {reason}")

            # Record the replanning trigger
            state_manager.record_action({
                'action_type': 'replanning_triggered',
                'trigger_reason': reason,
                'timestamp': datetime.now().isoformat()
            })

            # Update last replanning time
            self._last_replanning_check['last_replan_time'] = time.time()

            # In a full implementation, this would notify the agent orchestrator
            # to initiate a new planning cycle
            # For now, we'll just log it and update state

            # Trigger objective re-evaluation to get fresh baseline
            self._trigger_objective_reevaluation()

        except Exception as e:
            logger.error(f"Error triggering replanning: {e}")

    def _trigger_objective_reevaluation(self) -> None:
        """Trigger re-evaluation of all objectives to get fresh baseline"""
        try:
            logger.info("Triggering objective re-evaluation after replanning trigger")

            # Get current state and re-evaluate all objectives
            inventory_state = state_manager.get_inventory()
            shipment_state = state_manager.get_shipment()

            # Re-evaluate inventory objective
            if inventory_state:
                # Create metrics that reflect current state
                current_metrics = {
                    'total_inventory_units': sum(item.get('quantity', 0) for item in inventory_state.values()),
                    'average_inventory_per_item': sum(item.get('quantity', 0) for item in inventory_state.values()) / len(inventory_state) if inventory_state else 0,
                    'stockout_items': sum(1 for item in inventory_state.values() if item.get('quantity', 0) <= 0),
                    'low_stock_items': sum(1 for item in inventory_state.values() if item.get('quantity', 0) < 10)
                }
                goal_manager.evaluate_objective_progress('inventory_levels', current_metrics)

            # Re-evaluate delivery objective
            if shipment_state:
                current_metrics = {
                    'average_delay_hours': sum(item.get('delay_hours', 0) for item in shipment_state.values()) / len(shipment_state) if shipment_state else 0,
                    'on_time_shipment_percentage': sum(1 for item in shipment_state.values() if item.get('delay_hours', 0) <= 24) / len(shipment_state) * 100 if shipment_state else 100,
                    'total_shipments': len(shipment_state),
                    'max_delay_hours': max((item.get('delay_hours', 0) for item in shipment_state.values()), default=0)
                }
                goal_manager.evaluate_objective_progress('delivery_timelines', current_metrics)

            # For cost and carbon objectives, we'll use placeholder current metrics
            # In a real system, these would come from financial/environmental systems
            goal_manager.evaluate_objective_progress('cost_constraints', {
                'estimated_logistics_cost_per_unit': 11.0,  # Placeholder
                'cost_variance': 0.03
            })

            goal_manager.evaluate_objective_progress('carbon_constraints', {
                'estimated_carbon_per_shipment': 85.0,  # Placeholder
                'carbon_reduction_rate': 0.03
            })

            logger.info("Objective re-evaluation completed")

        except Exception as e:
            logger.error(f"Error triggering objective re-evaluation: {e}")

    def get_replanning_status(self) -> Dict[str, Any]:
        """Get current status of the replanning trigger"""
        return {
            'replanning_active': not self._stop_replanning.is_set(),
            'last_replan_time': self._last_replanning_check.get('last_replan_time'),
            'last_state_check': self._last_replanning_check.get('last_state_summary'),
            'replanning_history_count': len(self._replanning_history),
            'thresholds': self.replanning_thresholds.copy()
        }

    def get_replanning_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get replanning history"""
        with getattr(self, '_queue_lock', threading.Lock()):
            history = self._replanning_history[-limit:] if len(self._replanning_history) > limit else self._replanning_history
            return history

# Global replanning trigger instance
replanning_trigger = ReplanningTrigger()