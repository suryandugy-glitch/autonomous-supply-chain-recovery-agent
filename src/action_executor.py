"""
Action Executor for the Autonomous Supply Chain Recovery Agent
Executes simulated recovery actions via provided endpoints and tracks action execution status
"""

import time
import threading
import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .config import config
from .state_manager import state_manager
from .optimization import optimization_engine
from .utils import setup_logging, safe_request

# Setup logger
logger = setup_logging(__name__)

class ActionExecutor:
    """Executes recovery actions and monitors their completion"""

    def __init__(self):
        self._execution_thread = None
        self._stop_execution = threading.Event()
        self._execution_queue = []  # Queue of actions to execute
        self._queue_lock = threading.Lock()
        self._active_executions = {}  # Currently executing actions
        self._execution_history = []

        # Execution intervals
        self.execution_interval = config.get_agent_param('monitoring_interval') or 30

        # Tool endpoints
        self.endpoints = {
            'action_endpoint': config.get_tool_endpoint('action_endpoint'),
            'verification_endpoint': config.get_tool_endpoint('verification_endpoint')
        }

        # Action timeout configuration
        self.action_timeout = config.get_agent_param('action_timeout_seconds') or 300  # 5 minutes default

    def start_execution(self) -> None:
        """Start the execution thread"""
        if self._execution_thread is not None and self._execution_thread.is_alive():
            logger.warning("Action executor is already running")
            return

        logger.info("Starting action executor...")
        self._stop_execution.clear()
        self._execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self._execution_thread.start()

    def stop_execution(self) -> None:
        """Stop the execution thread"""
        logger.info("Stopping action executor...")
        self._stop_execution.set()
        if self._execution_thread:
            self._execution_thread.join(timeout=5.0)

    def queue_action_for_execution(self, action_plan: Dict[str, Any]) -> None:
        """Add an action to the execution queue"""
        with self._queue_lock:
            # Create a unique action ID
            action_id = f"action_{int(time.time())}_{len(self._execution_queue)}"
            action_plan['action_id'] = action_id
            action_plan['queued_at'] = datetime.now().isoformat()

            self._execution_queue.append(action_plan)
            logger.info(f"Queued action for execution: {action_plan.get('description', 'Unknown')} (ID: {action_id})")

    def _execution_loop(self) -> None:
        """Main execution loop"""
        logger.info("Execution loop started")

        while not self._stop_execution.is_set():
            try:
                # Process any queued actions
                action_to_execute = None
                with self._queue_lock:
                    if self._execution_queue:
                        action_to_execute = self._execution_queue.pop(0)

                if action_to_execute:
                    self._execute_action(action_to_execute)
                else:
                    # No actions to execute, check on active executions
                    self._check_active_executions()
                    time.sleep(5)  # Sleep briefly when idle

            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                time.sleep(5)  # Short sleep on error

        # Clean up any remaining active executions on shutdown
        self._shutdown_active_executions()
        logger.info("Execution loop stopped")

    def _execute_action(self, action_plan: Dict[str, Any]) -> None:
        """Execute a specific action"""
        action_id = action_plan.get('action_id')
        description = action_plan.get('description', 'Unknown action')
        action_type = action_plan.get('alternative_type', action_plan.get('action_type', 'unknown'))

        logger.info(f"Executing action: {description} (ID: {action_id}, Type: {action_type})")

        try:
            # Record the start of execution
            state_manager.record_action({
                'action_type': 'execution_started',
                'action_id': action_id,
                'description': description,
                'action_plan': action_plan,
                'timestamp': datetime.now().isoformat()
            })

            # Add to active executions
            with self._queue_lock:
                self._active_executions[action_id] = {
                    'action_plan': action_plan,
                    'started_at': datetime.now(),
                    'status': 'executing',
                    'progress': 0.0
                }

            # Try to use the provided action endpoint first
            execution_result = self._use_action_endpoint(action_plan)

            if execution_result:
                # Action endpoint succeeded
                self._complete_action_execution(action_id, action_plan, execution_result, used_endpoint=True)
            else:
                # Action endpoint failed or unavailable, use internal execution simulation
                logger.info("Using internal action execution simulation")
                execution_result = self._simulate_action_execution(action_plan)
                self._complete_action_execution(action_id, action_plan, execution_result, used_endpoint=False)

        except Exception as e:
            logger.error(f"Error executing action {action_id}: {e}")
            self._fail_action_execution(action_id, action_plan, str(e))

    def _use_action_endpoint(self, action_plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use the provided action endpoint via API"""
        try:
            logger.debug("Attempting to use external action endpoint")

            # Prepare request for action endpoint
            request_data = {
                'action_type': action_plan.get('alternative_type', 'unknown'),
                'parameters': action_plan,
                'timestamp': datetime.now().isoformat()
            }

            # Call action endpoint
            response = safe_request(
                'POST',
                self.endpoints['action_endpoint'],
                json=request_data,
                timeout=self.action_timeout
            )

            if response and response.status_code in [200, 201, 202]:
                result = response.json()
                logger.info("Successfully used external action endpoint")
                return result
            else:
                logger.warning(f"External action endpoint returned status: {response.status_code if response else 'No response'}")
                return None

        except Exception as e:
            logger.error(f"Error using external action endpoint: {e}")
            return None

    def _simulate_action_execution(self, action_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate action execution when external endpoint is not available"""
        try:
            action_type = action_plan.get('alternative_type', 'unknown')
            description = action_plan.get('description', 'Unknown action')

            logger.info(f"Simulating execution of: {description}")

            # Simulate execution time based on action type
            base_execution_time = 2.0  # Base 2 seconds
            execution_time = base_execution_time

            # Adjust execution time based on action type
            if 'vendor' in action_type:
                execution_time = 3.0  # Vendor actions take longer
            elif 'shipping' in action_type or 'routing' in action_type:
                execution_time = 4.0  # Shipping actions take longer
            elif 'capacity' in action_type:
                execution_time = 5.0  # Capacity changes take longest
            elif 'forecast' in action_type or 'internal' in action_type:
                execution_time = 1.5  # Internal/planning actions are faster

            # Simulate the execution time (in reality, this would be non-blocking)
            # For simulation, we'll just note the expected time
            logger.debug(f"Action {action_plan.get('action_id')} simulated to take {execution_time} seconds")

            # Determine success based on action reliability and some randomness
            reliability = action_plan.get('reliability_score', 0.8)
            import random
            success_chance = reliability

            # Add some variability based on action type
            if 'expedited' in action_type:
                success_chance *= 0.9  # Expedited actions slightly less reliable
            if 'internal' in action_type:
                success_chance *= 1.1  # Internal actions more reliable
                success_chance = min(1.0, success_chance)

            success = random.random() < success_chance

            if success:
                result = {
                    'status': 'success',
                    'action_id': action_plan.get('action_id'),
                    'description': description,
                    'execution_time_seconds': execution_time,
                    'outputs': self._generate_action_outputs(action_plan),
                    'side_effects': self._generate_action_side_effects(action_plan),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                result = {
                    'status': 'failed',
                    'action_id': action_plan.get('action_id'),
                    'description': description,
                    'execution_time_seconds': execution_time,
                    'error_message': f'Action failed during execution (simulated)',
                    'timestamp': datetime.now().isoformat()
                }

            return result

        except Exception as e:
            logger.error(f"Error simulating action execution: {e}")
            return {
                'status': 'error',
                'action_id': action_plan.get('action_id'),
                'description': action_plan.get('description', 'Unknown'),
                'error_message': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _complete_action_execution(self, action_id: str, action_plan: Dict[str, Any],
                                 result: Dict[str, Any], used_endpoint: bool) -> None:
        """Complete action execution and record results"""
        try:
            execution_time = (datetime.now() - self._active_executions[action_id]['started_at']).total_seconds()

            # Update active execution status
            with self._queue_lock:
                if action_id in self._active_executions:
                    self._active_executions[action_id]['status'] = 'completed' if result.get('status') == 'success' else 'failed'
                    self._active_executions[action_id]['completed_at'] = datetime.now()
                    self._active_executions[action_id]['result'] = result
                    self._active_executions[action_id]['execution_time'] = execution_time

            # Record action completion in state manager
            state_manager.record_action({
                'action_type': 'execution_completed',
                'action_id': action_id,
                'description': action_plan.get('description'),
                'action_plan': action_plan,
                'execution_result': result,
                'used_external_endpoint': used_endpoint,
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat()
            })

            # If successful, trigger verification
            if result.get('status') == 'success':
                logger.info(f"Action {action_id} completed successfully, triggering verification")
                # In a full implementation, we would notify the verification module
                # For now, we'll just log it
            else:
                logger.warning(f"Action {action_id} failed: {result.get('error_message', 'Unknown error')}")

            # Move to execution history and remove from active
            with self._queue_lock:
                if action_id in self._active_executions:
                    self._execution_history.append(self._active_executions.pop(action_id))

            # Keep history bounded
            if len(self._execution_history) > 100:
                self._execution_history = self._execution_history[-100:]

        except Exception as e:
            logger.error(f"Error completing action execution: {e}")

    def _fail_action_execution(self, action_id: str, action_plan: Dict[str, Any],
                             error_message: str) -> None:
        """Handle action execution failure"""
        try:
            execution_time = (datetime.now() - self._active_executions[action_id]['started_at']).total_seconds()

            # Update active execution status
            with self._queue_lock:
                if action_id in self._active_executions:
                    self._active_executions[action_id]['status'] = 'failed'
                    self._active_executions[action_id]['completed_at'] = datetime.now()
                    self._active_executions[action_id]['error'] = error_message
                    self._active_executions[action_id]['execution_time'] = execution_time

            # Record action failure in state manager
            state_manager.record_action({
                'action_type': 'execution_failed',
                'action_id': action_id,
                'description': action_plan.get('description'),
                'action_plan': action_plan,
                'error_message': error_message,
                'execution_time_seconds': execution_time,
                'timestamp': datetime.now().isoformat()
            })

            logger.error(f"Action {action_id} failed: {error_message}")

            # Move to execution history and remove from active
            with self._queue_lock:
                if action_id in self._active_executions:
                    self._execution_history.append(self._active_executions.pop(action_id))

        except Exception as e:
            logger.error(f"Error failing action execution: {e}")

    def _check_active_executions(self) -> None:
        """Check on currently executing actions for timeouts or completion"""
        current_time = datetime.now()
        timed_out_actions = []

        with self._queue_lock:
            for action_id, execution_info in list(self._active_executions.items()):
                # Check for timeout
                execution_duration = (current_time - execution_info['started_at']).total_seconds()
                if execution_duration > self.action_timeout:
                    timed_out_actions.append((action_id, execution_info))

        # Handle timed out actions
        for action_id, execution_info in timed_out_actions:
            logger.warning(f"Action {action_id} timed out after {self.action_timeout} seconds")
            self._fail_action_execution(
                action_id,
                execution_info['action_plan'],
                f'Action timed out after {self.action_timeout} seconds'
            )

    def _shutdown_active_executions(self) -> None:
        """Shut down any active executions when stopping the executor"""
        with self._queue_lock:
            for action_id, execution_info in list(self._active_executions.items()):
                logger.info(f"Shutting down active action {action_id} during executor shutdown")
                self._fail_action_execution(
                    action_id,
                    execution_info['action_plan'],
                    'Action executor shutting down'
                )

    def _generate_action_outputs(self, action_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic outputs for a successful action execution"""
        action_type = action_plan.get('alternative_type', 'unknown')
        description = action_plan.get('description', '')

        outputs = {
            'action_completed': True,
            'completion_timestamp': datetime.now().isoformat()
        }

        # Generate type-specific outputs
        if 'vendor' in action_type and 'substitution' in action_type:
            outputs.update({
                'new_vendor_id': action_plan.get('alternative_vendor_id') or action_plan.get('vendor_id'),
                'new_vendor_name': action_plan.get('alternative_vendor_name') or action_plan.get('vendor_name', 'Unknown Vendor'),
                'effective_from': (datetime.now() + timedelta(days=1)).isoformat(),
                'transition_plan': 'Gradual transition over 7-14 days'
            })
        elif 'shipping' in action_type or 'routing' in action_type:
            outputs.update({
                'new_routing_instructions': 'Generated and transmitted to carrier',
                'estimated_time_saved_hours': action_plan.get('lead_time_days', 0) * 8,  # Convert days to hours
                'new_tracking_info': f"TRK{int(time.time())}"
            })
        elif 'capacity' in action_type:
            outputs.update({
                'additional_capacity_activated': action_plan.get('additional_capacity_per_day', 0),
                'activation_complete': True,
                'full_capacity_available_from': (datetime.now() + timedelta(days=action_plan.get('lead_time_days', 2))).isoformat()
            })
        elif 'forecast' in action_type:
            outputs.update({
                'forecast_improvement_achieved': True,
                'new_confidence_level': action_plan.get('target_confidence_level', 0.8),
                'improvement_methodology': 'Enhanced market intelligence and statistical modeling'
            })
        elif 'internal' in action_type and 'reallocation' in action_type:
            outputs.update({
                'quantity_reallocated': action_plan.get('available_quantity', 0),
                'source_locations': ['Warehouse A', 'Warehouse B'],  # Simplified
                'destination_locations': ['Distribution Center X'],
                'completion_timestamp': datetime.now().isoformat()
            })
        elif 'escalation' in action_type:
            outputs.update({
                'escalated_to': 'Human Supervisor',
                'escalation_time': datetime.now().isoformat(),
                'ticket_id': f"ESC{int(time.time())}",
                'expected_response_time_hours': 4
            })

        return outputs

    def _generate_action_side_effects(self, action_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate potential side effects of an action"""
        action_type = action_plan.get('alternative_type', 'unknown')
        side_effects = []

        # Common side effects
        if action_plan.get('estimated_cost', 0) > 100:
            side_effects.append({
                'type': 'financial',
                'description': 'Increased execution cost',
                'impact': 'medium',
                'mitigation': 'Cost justified by disruption resolution'
            })

        if action_plan.get('lead_time_days', 0) > 5:
            side_effects.append({
                'type': 'temporal',
                'description': 'Extended lead time may affect downstream operations',
                'impact': 'low',
                'mitigation': 'Communicate timeline changes to stakeholders'
            })

        if action_plan.get('carbon_factor', 1.0) > 1.2:
            side_effects.append({
                'type': 'environmental',
                'description': 'Increased carbon footprint',
                'impact': 'low',
                'mitigation': 'Consider offsetting or future optimization'
            })

        # Type-specific side effects
        if 'vendor' in action_type and 'substitution' in action_type:
            side_effects.append({
                'type': 'operational',
                'description': 'May require updating vendor contracts and purchase orders',
                'impact': 'medium',
                'mitigation': 'Procurement team to handle contract updates'
            })
            side_effects.append({
                'type': 'relational',
                'description': 'Original vendor relationship may be affected',
                'impact': 'low',
                'mitigation': 'Maintain professional communication and consider future opportunities'
            })

        if 'expedited' in action_plan.get('alternative_type', ''):
            side_effects.append({
                'type': 'financial',
                'description': 'Expedited shipping costs significantly higher',
                'impact': 'high',
                'mitigation': 'Use only for critical disruptions, monitor cost impact'
            })

        if action_plan.get('requires_human_input', False):
            side_effects.append({
                'type': 'operational',
                'description': 'Requires human intervention and decision making',
                'impact': 'medium',
                'mitigation': 'Ensure appropriate personnel are notified and available'
            })

        return side_effects

    def get_active_executions(self) -> List[Dict[str, Any]]:
        """Get currently executing actions"""
        with self._queue_lock:
            return [
                {
                    'action_id': action_id,
                    'description': exec_info['action_plan'].get('description'),
                    'action_type': exec_info['action_plan'].get('alternative_type'),
                    'started_at': exec_info['started_at'].isoformat(),
                    'duration_seconds': (datetime.now() - exec_info['started_at']).total_seconds(),
                    'status': exec_info['status']
                }
                for action_id, exec_info in self._active_executions.items()
            ]

    def get_execution_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get execution history"""
        with self._queue_lock:
            history = self._execution_history[-limit:] if len(self._execution_history) > limit else self._execution_history
            return [
                {
                    'action_id': exec_info.get('action_id', 'unknown'),
                    'description': exec_info.get('action_plan', {}).get('description', 'Unknown'),
                    'action_type': exec_info.get('action_plan', {}).get('alternative_type', 'unknown'),
                    'started_at': exec_info.get('started_at', datetime.now()).isoformat(),
                    'completed_at': exec_info.get('completed_at', datetime.now()).isoformat(),
                    'status': exec_info.get('status', 'unknown'),
                    'execution_time_seconds': exec_info.get('execution_time', 0),
                    'success': exec_info.get('status') == 'completed'
                }
                for exec_info in history
            ]

    def get_execution_status(self) -> Dict[str, Any]:
        """Get current status of the action executor"""
        with self._queue_lock:
            active_count = len(self._active_executions)
            queued_count = len(self._execution_queue)

        return {
            'execution_active': not self._stop_execution.is_set(),
            'active_executions': active_count,
            'queued_executions': queued_count,
            'execution_history_size': len(self._execution_history),
            'action_timeout_seconds': self.action_timeout
        }

# Global action executor instance
action_executor = ActionExecutor()