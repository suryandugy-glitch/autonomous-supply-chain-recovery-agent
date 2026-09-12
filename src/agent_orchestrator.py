"""
Agent Orchestrator for the Autonomous Supply Chain Recovery Agent
Coordinates the workflow between all components and implements the main agentic loop:
Monitor → Detect → Investigate → Optimize → Execute → Verify → (Replan if needed)
"""

import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from .config import config
from .state_manager import state_manager
from .goal_manager import goal_manager
from .monitoring import monitoring_module
from .disruption_detector import disruption_detector
from .alternative_investigator import alternative_investigator
from .optimization import optimization_engine
from .action_executor import action_executor
from .verification import verification_module
from .replanning_trigger import replanning_trigger
from .utils import setup_logging

# Setup logger
logger = setup_logging(__name__)

class AgentOrchestrator:
    """Orchestrates the agentic workflow for supply chain recovery"""

    def __init__(self):
        self._orchestrator_thread = None
        self._stop_orchestrator = threading.Event()
        self._cycle_count = 0
        self._last_cycle_time = None
        self._is_running = False

        # Cycle timing
        self.min_cycle_time = config.get_agent_param('monitoring_interval') or 30  # Minimum time between cycles
        self.max_cycle_time = 300  # Maximum time between cycles (5 minutes)

        # Component references
        self.components = {
            'monitoring': monitoring_module,
            'disruption_detector': disruption_detector,
            'alternative_investigator': alternative_investigator,
            'optimization_engine': optimization_engine,
            'action_executor': action_executor,
            'verification_module': verification_module,
            'replanning_trigger': replanning_trigger,
            'goal_manager': goal_manager,
            'state_manager': state_manager
        }

    def start(self) -> None:
        """Start the agent orchestrator and all components"""
        if self._is_running:
            logger.warning("Agent orchestrator is already running")
            return

        logger.info("Starting agent orchestrator and all components...")
        self._is_running = True
        self._stop_orchestrator.clear()

        # Start all components in the right order
        self._start_components()

        # Start the main orchestrator loop
        self._orchestrator_thread = threading.Thread(target=self._orchestrator_loop, daemon=True)
        self._orchestrator_thread.start()

        logger.info("Agent orchestrator started successfully")

    def stop(self) -> None:
        """Stop the agent orchestrator and all components"""
        if not self._is_running:
            logger.warning("Agent orchestrator is not running")
            return

        logger.info("Stopping agent orchestrator and all components...")
        self._stop_orchestrator.set()
        self._is_running = False

        # Stop the orchestrator thread
        if self._orchestrator_thread:
            self._orchestrator_thread.join(timeout=5.0)

        # Stop all components in reverse order
        self._stop_components()

        logger.info("Agent orchestrator stopped successfully")

    def _start_components(self) -> None:
        """Start all components in the correct dependency order"""
        try:
            # Start with foundational components
            logger.info("Starting state manager and goal manager...")
            # These are passive components that don't need explicit start

            # Start monitoring to gather initial state
            logger.info("Starting monitoring module...")
            self.components['monitoring'].start_monitoring()

            # Start disruption detection (depends on monitoring data)
            logger.info("Starting disruption detector...")
            self.components['disruption_detector'].start_detection()

            # Start alternative investigation (triggered by disruptions)
            logger.info("Starting alternative investigator...")
            self.components['alternative_investigator'].start_investigation()

            # Start optimization engine (triggered by investigations)
            logger.info("Starting optimization engine...")
            self.components['optimization_engine'].start_optimization()

            # Start action executor (triggered by optimization)
            logger.info("Starting action executor...")
            self.components['action_executor'].start_execution()

            # Start verification module (triggered by action execution)
            logger.info("Starting verification module...")
            self.components['verification_module'].start_verification()

            # Start replanning trigger (monitoring for plan validity)
            logger.info("Starting replanning trigger...")
            self.components['replanning_trigger'].start_replanning_monitoring()

            logger.info("All components started successfully")

        except Exception as e:
            logger.error(f"Error starting components: {e}")
            self._stop_components()  # Try to stop what we started
            raise

    def _stop_components(self) -> None:
        """Stop all components in reverse order"""
        try:
            # Stop in reverse order of dependencies
            logger.info("Stopping replanning trigger...")
            self.components['replanning_trigger'].stop_replanning_monitoring()

            logger.info("Stopping verification module...")
            self.components['verification_module'].stop_verification()

            logger.info("Stopping action executor...")
            self.components['action_executor'].stop_execution()

            logger.info("Stopping optimization engine...")
            self.components['optimization_engine'].stop_optimization()

            logger.info("Stopping alternative investigator...")
            self.components['alternative_investigator'].stop_investigation()

            logger.info("Stopping disruption detector...")
            self.components['disruption_detector'].stop_detection()

            logger.info("Stopping monitoring module...")
            self.components['monitoring'].stop_monitoring()

            logger.info("All components stopped")

        except Exception as e:
            logger.error(f"Error stopping components: {e}")

    def _orchestrator_loop(self) -> None:
        """Main orchestrator loop that coordinates the agentic workflow"""
        logger.info("Agent orchestrator loop started")
        last_cycle_time = time.time()

        while not self._stop_orchestrator.is_set():
            try:
                cycle_start = time.time()

                # Execute one cycle of the agentic workflow
                self._execute_agentic_cycle()

                cycle_end = time.time()
                cycle_duration = cycle_end - cycle_start

                # Update cycle statistics
                self._cycle_count += 1
                self._last_cycle_time = datetime.now()

                # Calculate sleep time to maintain minimum cycle time
                sleep_time = max(0, self.min_cycle_time - cycle_duration)
                if sleep_time > 0:
                    time.sleep(sleep_time)

                # Log periodic status
                if self._cycle_count % 10 == 0:  # Every 10 cycles
                    logger.info(f"Agent orchestrator completed {self._cycle_count} cycles. "
                              f"Last cycle duration: {cycle_duration:.2f}s")

            except Exception as e:
                logger.error(f"Error in orchestrator loop: {e}")
                time.sleep(5)  # Short sleep on error to prevent tight loop

        logger.info("Agent orchestrator loop stopped")

    def _execute_agentic_cycle(self) -> None:
        """Execute one complete cycle of the agentic workflow"""
        try:
            logger.debug("Starting agentic cycle")

            # Phase 1: Monitoring (handled by background threads, just check status)
            monitoring_status = self.components['monitoring'].get_current_state_summary()
            logger.debug(f"Monitoring status: {monitoring_status}")

            # Phase 2: Disruption Detection (handled by background threads)
            disruption_status = self.components['disruption_detector'].get_disruption_summary()
            logger.debug(f"Disruption detection status: {disruption_status}")

            # Phase 3: Check if we need to investigate any disruptions
            active_disruptions = self.components['disruption_detector'].get_active_disruptions()
            if active_disruptions:
                logger.info(f"Found {len(active_disruptions)} active disruptions to investigate")
                for disruption in active_disruptions[:3]:  # Limit to top 3 to avoid overload
                    # Queue disruption for investigation
                    self.components['alternative_investigator'].queue_disruption_for_investigation(disruption)

            # Phase 4: Check investigation results and optimize
            # (This is handled by background threads, but we can check status)
            inv_status = self.components['alternative_investigator'].get_investigation_status()
            opt_status = self.components['optimization_engine'].get_optimization_status()
            logger.debug(f"Investigation status: {inv_status}")
            logger.debug(f"Optimization status: {opt_status}")

            # Phase 5: Check optimization results and execute actions
            # (Handled by background threads)
            exec_status = self.components['action_executor'].get_execution_status()
            logger.debug(f"Execution status: {exec_status}")

            # Phase 6: Check execution results and verify
            # (Handled by background threads)
            verif_status = self.components['verification_module'].get_verification_status()
            logger.debug(f"Verification status: {verif_status}")

            # Phase 7: Check verification results and update goals
            # (Handled by background threads via verification module)
            goal_status = self.components['goal_manager'].get_overall_goal_progress()
            logger.debug(f"Goal progress: {goal_status.get('status', 'unknown')} "
                         f"({goal_status.get('objectives_met', 0)}/{goal_status.get('total_objectives', 0)} objectives met)")

            # Phase 8: Check if replanning is needed
            # (Handled by background threads)
            replan_status = self.components['replanning_trigger'].get_replanning_status()
            logger.debug(f"Replanning status: {replan_status}")

            # Periodic state checkpoint (every 50 cycles)
            if self._cycle_count % 50 == 0:
                self.components['state_manager'].save_state()
                logger.debug("State checkpoint saved")

        except Exception as e:
            logger.error(f"Error executing agentic cycle: {e}")

    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the agent and all components"""
        try:
            status = {
                'agent_orchestrator': {
                    'is_running': self._is_running,
                    'cycle_count': self._cycle_count,
                    'last_cycle_time': self._last_cycle_time.isoformat() if self._last_cycle_time else None,
                    'status': 'running' if self._is_running else 'stopped'
                },
                'state_manager': self.components['state_manager'].get_state_summary(),
                'goal_manager': self.components['goal_manager'].get_overall_goal_progress(),
                'monitoring': self.components['monitoring'].get_current_state_summary(),
                'disruption_detector': self.components['disruption_detector'].get_disruption_summary(),
                'alternative_investigator': self.components['alternative_investigator'].get_investigation_status(),
                'optimization_engine': self.components['optimization_engine'].get_optimization_status(),
                'action_executor': self.components['action_executor'].get_execution_status(),
                'verification_module': self.components['verification_module'].get_verification_status(),
                'replanning_trigger': self.components['replanning_trigger'].get_replanning_status()
            }
            return status
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return {'error': str(e)}

    def get_agentic_workflow_summary(self) -> Dict[str, Any]:
        """Get a summary demonstrating the agentic workflow"""
        try:
            # Get recent actions to show the workflow in action
            recent_actions = self.components['state_manager'].get_recent_actions(limit=20)

            # Categorize actions by type to show the workflow
            action_types = {}
            for action in recent_actions:
                action_type = action.get('action_type', 'unknown')
                if action_type not in action_types:
                    action_types[action_type] = []
                action_types[action_type].append(action)

            # Show objective progress
            goal_progress = self.components['goal_manager'].get_overall_goal_progress()

            # Show recent disruptions
            recent_disruptions = self.components['state_manager'].get_recent_disruptions(limit=5)

            return {
                'workflow_description': 'Monitor → Detect → Investigate → Optimize → Execute → Verify → (Replan if needed)',
                'recent_actions_by_type': {
                    action_type: len(actions) for action_type, actions in action_types.items()
                },
                'goal_progress': goal_progress,
                'recent_disruptions': [
                    {
                        'type': d.get('type'),
                        'description': d.get('description'),
                        'severity': d.get('severity'),
                        'timestamp': d.get('timestamp')
                    }
                    for d in recent_disruptions
                ],
                'agent_cycles_completed': self._cycle_count,
                'agent_uptime_seconds': (
                    (datetime.now() - self._last_cycle_time).total_seconds()
                    if self._last_cycle_time else 0
                ) if self._is_running else 0
            }
        except Exception as e:
            logger.error(f"Error getting agentic workflow summary: {e}")
            return {'error': str(e)}

# Global agent orchestrator instance
agent_orchestrator = AgentOrchestrator()