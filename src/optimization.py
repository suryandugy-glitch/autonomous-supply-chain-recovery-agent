"""
Optimization Engine for the Autonomous Supply Chain Recovery Agent
Uses provided optimization tools to evaluate alternatives considering multi-objective constraints
(cost, delivery time, carbon emissions) and recommends optimal recovery action
"""

import time
import threading
import json
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from .config import config
from .state_manager import state_manager
from .utils import setup_logging, safe_request

# Setup logger
logger = setup_logging(__name__)

class OptimizationEngine:
    """Optimizes recovery actions based on multiple objectives and constraints"""

    def __init__(self):
        self._optimization_thread = None
        self._stop_optimization = threading.Event()
        self._optimization_queue = []  # Queue of optimization requests
        self._queue_lock = threading.Lock()
        self._last_optimization = {}
        self._optimization_cache = {}

        # Optimization intervals
        self.optimization_interval = config.get_agent_param('monitoring_interval') or 30

        # Tool endpoints
        self.endpoints = {
            'optimization_tool': config.get_tool_endpoint('optimization_tool'),
            'verification_endpoint': config.get_tool_endpoint('verification_endpoint')
        }

        # Weights for multi-objective optimization (can be adjusted)
        self.objective_weights = {
            'cost': 0.4,           # 40% weight on cost
            'lead_time': 0.3,      # 30% weight on lead time/speed
            'reliability': 0.2,    # 20% weight on reliability
            'carbon': 0.1          # 10% weight on carbon footprint
        }

    def start_optimization(self) -> None:
        """Start the optimization thread"""
        if self._optimization_thread is not None and self._optimization_thread.is_alive():
            logger.warning("Optimization engine is already running")
            return

        logger.info("Starting optimization engine...")
        self._stop_optimization.clear()
        self._optimization_thread = threading.Thread(target=self._optimization_loop, daemon=True)
        self._optimization_thread.start()

    def stop_optimization(self) -> None:
        """Stop the optimization thread"""
        logger.info("Stopping optimization engine...")
        self._stop_optimization.set()
        if self._optimization_thread:
            self._optimization_thread.join(timeout=5.0)

    def queue_optimization_request(self, disruption: Dict[str, Any],
                                 alternatives: List[Dict[str, Any]]) -> None:
        """Add an optimization request to the queue"""
        with self._queue_lock:
            # Avoid duplicating optimization for the same disruption recently
            disruption_key = f"{disruption.get('disruption_type')}_{disruption.get('entity_type')}_{disruption.get('entity_id')}"
            last_optimized = self._last_optimization.get(disruption_key, 0)

            # Only queue if enough time has passed (5 minutes) or never optimized
            if time.time() - last_optimized > 300 or last_optimized == 0:
                self._optimization_queue.append({
                    'disruption': disruption,
                    'alternatives': alternatives
                })
                self._last_optimization[disruption_key] = time.time()
                logger.info(f"Queued optimization request for disruption: {disruption.get('description')}")

    def _optimization_loop(self) -> None:
        """Main optimization loop"""
        logger.info("Optimization loop started")

        while not self._stop_optimization.is_set():
            try:
                # Process any queued optimization requests
                optimization_request = None
                with self._queue_lock:
                    if self._optimization_queue:
                        optimization_request = self._optimization_queue.pop(0)

                if optimization_request:
                    self._process_optimization_request(
                        optimization_request['disruption'],
                        optimization_request['alternatives']
                    )
                else:
                    # No optimizations to process, sleep briefly
                    time.sleep(5)

            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                time.sleep(5)  # Short sleep on error

        logger.info("Optimization loop stopped")

    def _process_optimization_request(self, disruption: Dict[str, Any],
                                    alternatives: List[Dict[str, Any]]) -> None:
        """Process an optimization request to find the best alternative"""
        try:
            logger.info(f"Processing optimization for disruption: {disruption.get('description')} with {len(alternatives)} alternatives")

            # Try to use the provided optimization tool first
            tool_result = self._use_optimization_tool(disruption, alternatives)

            if tool_result:
                # Tool succeeded, use its result
                self._record_optimization_result(disruption, alternatives, tool_result, used_tool=True)
            else:
                # Tool failed or unavailable, use internal optimization
                logger.info("Using internal optimization algorithm")
                internal_result = self._internal_optimization(disruption, alternatives)
                self._record_optimization_result(disruption, alternatives, internal_result, used_tool=False)

        except Exception as e:
            logger.error(f"Error processing optimization request: {e}")

    def _use_optimization_tool(self, disruption: Dict[str, Any],
                             alternatives: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Use the provided optimization tool via API"""
        try:
            logger.debug("Attempting to use external optimization tool")

            # Prepare request for optimization tool
            request_data = {
                'disruption': disruption,
                'alternatives': alternatives,
                'objective_weights': self.objective_weights,
                'constraints': self._get_constraints_for_disruption(disruption),
                'timestamp': datetime.now().isoformat()
            }

            # Call optimization tool
            response = safe_request(
                'POST',
                self.endpoints['optimization_tool'],
                json=request_data,
                timeout=30
            )

            if response and response.status_code == 200:
                result = response.json()
                logger.info("Successfully used external optimization tool")
                return result
            else:
                logger.warning(f"External optimization tool returned status: {response.status_code if response else 'No response'}")
                return None

        except Exception as e:
            logger.error(f"Error using external optimization tool: {e}")
            return None

    def _internal_optimization(self, disruption: Dict[str, Any],
                             alternatives: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform internal multi-objective optimization"""
        try:
            logger.debug("Performing internal multi-objective optimization")

            if not alternatives:
                return self._create_no_alternatives_result()

            # Normalize and score each alternative
            scored_alternatives = []

            for alt in alternatives:
                score = self._calculate_alternative_score(alt, disruption)
                scored_alternatives.append({
                    'alternative': alt,
                    'score': score,
                    'details': self._get_score_details(alt, disruption)
                })

            # Sort by score (descending - higher is better)
            scored_alternatives.sort(key=lambda x: x['score'], reverse=True)

            # Get the best alternative
            best = scored_alternatives[0] if scored_alternatives else None

            if not best:
                return self._create_no_alternatives_result()

            # Prepare result
            result = {
                'recommended_alternative': best['alternative'],
                'alternative_score': best['score'],
                'score_details': best['details'],
                'all_alternatives_scored': [
                    {
                        'alternative': item['alternative'],
                        'score': item['score'],
                        'rank': idx + 1
                    }
                    for idx, item in enumerate(scored_alternatives)
                ],
                'optimization_method': 'internal_multi_objective',
                'timestamp': datetime.now().isoformat(),
                'weights_used': self.objective_weights.copy(),
                'total_alternatives_considered': len(alternatives)
            }

            return result

        except Exception as e:
            logger.error(f"Error in internal optimization: {e}")
            return self._create_error_result(str(e))

    def _calculate_alternative_score(self, alternative: Dict[str, Any],
                                   disruption: Dict[str, Any]) -> float:
        """Calculate a normalized score for an alternative based on multiple objectives"""
        try:
            # Extract alternative attributes with defaults
            cost = alternative.get('estimated_cost', 0.0)
            lead_time = alternative.get('lead_time_days', 7)
            reliability = alternative.get('reliability_score', 0.5)
            carbon = alternative.get('carbon_factor', 1.0)
            capacity = alternative.get('available_quantity', alternative.get('capacity_available', 100))

            # Get disruption context for normalization
            disruption_type = disruption.get('disruption_type', '')
            entity_type = disruption.get('entity_type', '')
            entity_id = disruption.get('entity_id', '')

            # Define normalization ranges (these would ideally come from historical data or configuration)
            normalization_ranges = self._get_normalization_ranges(disruption_type, entity_type)

            # Normalize each factor to 0-1 scale (where 1 is best)
            normalized_cost = self._normalize_cost(cost, normalization_ranges.get('cost', {'min': 0, 'max': 100}))
            normalized_lead_time = self._normalize_lead_time(lead_time, normalization_ranges.get('lead_time', {'min': 0, 'max': 30}))
            normalized_reliability = reliability  # Already 0-1 scale
            normalized_carbon = self._normalize_carbon(carbon, normalization_ranges.get('carbon', {'min': 0.5, 'max': 2.0}))
            normalized_capacity = self._normalize_capacity(capacity, normalization_ranges.get('capacity', {'min': 0, 'max': 1000}))

            # Apply weights
            weighted_score = (
                self.objective_weights['cost'] * normalized_cost +
                self.objective_weights['lead_time'] * normalized_lead_time +
                self.objective_weights['reliability'] * normalized_reliability +
                self.objective_weights['carbon'] * normalized_carbon
            )

            # Capacity bonus - only add if we have sufficient capacity
            capacity_factor = min(1.0, capacity / max(100, capacity)) if capacity > 0 else 0.0
            final_score = weighted_score * (0.8 + 0.2 * capacity_factor)  # Capacity affects up to 20% of score

            return max(0.0, min(1.0, final_score))  # Ensure score is between 0 and 1

        except Exception as e:
            logger.error(f"Error calculating alternative score: {e}")
            return 0.0

    def _get_normalization_ranges(self, disruption_type: str, entity_type: str) -> Dict[str, Dict[str, float]]:
        """Get normalization ranges for different disruption types"""
        # Base ranges
        base_ranges = {
            'cost': {'min': 0.0, 'max': 1000.0},      # $0 to $1000
            'lead_time': {'min': 0.0, 'max': 30.0},   # 0 to 30 days
            'reliability': {'min': 0.0, 'max': 1.0},  # 0 to 1 (already normalized)
            'carbon': {'min': 0.5, 'max': 2.0},       # 0.5x to 2x baseline
            'capacity': {'min': 0.0, 'max': 1000.0}   # 0 to 1000 units
        }

        # Adjust ranges based on disruption type
        if disruption_type in ['stockout', 'low_inventory']:
            # For inventory issues, cost and lead time are more critical
            base_ranges['cost']['max'] = 500.0
            base_ranges['lead_time']['max'] = 14.0
        elif disruption_type in ['delivery_delay', 'shipment_issue']:
            # For shipping issues, lead time and reliability are critical
            base_ranges['lead_time']['max'] = 7.0
            base_ranges['reliability']['min'] = 0.7
        elif disruption_type in ['vendor_reliability_issue', 'vendor_lead_time_issue', 'vendor_deactivation']:
            # For vendor issues, all factors matter but reliability is key
            base_ranges['reliability']['min'] = 0.6
        elif disruption_type in ['demand_forecast_uncertainty', 'demand_forecast_spike']:
            # For demand issues, capacity and cost are important
            base_ranges['capacity']['max'] = 5000.0
            base_ranges['cost']['max'] = 2000.0

        return base_ranges

    def _normalize_cost(self, cost: float, range_dict: Dict[str, float]) -> float:
        """Normalize cost to 0-1 scale (lower cost = higher score)"""
        min_cost, max_cost = range_dict['min'], range_dict['max']
        if max_cost <= min_cost:
            return 1.0 if cost <= min_cost else 0.0

        # Invert so lower cost gets higher score
        normalized = 1.0 - ((cost - min_cost) / (max_cost - min_cost))
        return max(0.0, min(1.0, normalized))

    def _normalize_lead_time(self, lead_time: float, range_dict: Dict[str, float]) -> float:
        """Normalize lead time to 0-1 scale (shorter time = higher score)"""
        min_time, max_time = range_dict['min'], range_dict['max']
        if max_time <= min_time:
            return 1.0 if lead_time <= min_time else 0.0

        # Invert so shorter lead time gets higher score
        normalized = 1.0 - ((lead_time - min_time) / (max_time - min_time))
        return max(0.0, min(1.0, normalized))

    def _normalize_carbon(self, carbon: float, range_dict: Dict[str, float]) -> float:
        """Normalize carbon factor to 0-1 scale (lower carbon = higher score)"""
        min_carbon, max_carbon = range_dict['min'], range_dict['max']
        if max_carbon <= min_carbon:
            return 1.0 if carbon <= min_carbon else 0.0

        # Invert so lower carbon gets higher score
        normalized = 1.0 - ((carbon - min_carbon) / (max_carbon - min_carbon))
        return max(0.0, min(1.0, normalized))

    def _normalize_capacity(self, capacity: float, range_dict: Dict[str, float]) -> float:
        """Normalize capacity to 0-1 scale (higher capacity = higher score)"""
        min_cap, max_cap = range_dict['min'], range_dict['max']
        if max_cap <= min_cap:
            return 1.0 if capacity >= min_cap else 0.0

        normalized = (capacity - min_cap) / (max_cap - min_cap)
        return max(0.0, min(1.0, normalized))

    def _get_score_details(self, alternative: Dict[str, Any],
                         disruption: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed breakdown of how the score was calculated"""
        # Extract alternative attributes
        cost = alternative.get('estimated_cost', 0.0)
        lead_time = alternative.get('lead_time_days', 7)
        reliability = alternative.get('reliability_score', 0.5)
        carbon = alternative.get('carbon_factor', 1.0)
        capacity = alternative.get('available_quantity', alternative.get('capacity_available', 100))

        # Get normalization ranges
        disruption_type = disruption.get('disruption_type', '')
        entity_type = disruption.get('entity_type', '')
        normalization_ranges = self._get_normalization_ranges(disruption_type, entity_type)

        # Calculate normalized values
        norm_cost = self._normalize_cost(cost, normalization_ranges.get('cost', {'min': 0, 'max': 100}))
        norm_lead_time = self._normalize_lead_time(lead_time, normalization_ranges.get('lead_time', {'min': 0, 'max': 30}))
        norm_reliability = reliability
        norm_carbon = self._normalize_carbon(carbon, normalization_ranges.get('carbon', {'min': 0.5, 'max': 2.0}))
        norm_capacity = self._normalize_capacity(capacity, normalization_ranges.get('capacity', {'min': 0, 'max': 1000}))

        # Calculate weighted components
        cost_component = self.objective_weights['cost'] * norm_cost
        lead_time_component = self.objective_weights['lead_time'] * norm_lead_time
        reliability_component = self.objective_weights['reliability'] * norm_reliability
        carbon_component = self.objective_weights['carbon'] * norm_carbon

        return {
            'raw_values': {
                'cost': cost,
                'lead_time_days': lead_time,
                'reliability_score': reliability,
                'carbon_factor': carbon,
                'capacity': capacity
            },
            'normalized_values': {
                'cost': norm_cost,
                'lead_time': norm_lead_time,
                'reliability': norm_reliability,
                'carbon': norm_carbon,
                'capacity': norm_capacity
            },
            'weighted_components': {
                'cost': cost_component,
                'lead_time': lead_time_component,
                'reliability': reliability_component,
                'carbon': carbon_component
            },
            'total_weighted_score': cost_component + lead_time_component + reliability_component + carbon_component,
            'objective_weights_used': self.objective_weights.copy()
        }

    def _get_constraints_for_disruption(self, disruption: Dict[str, Any]) -> Dict[str, Any]:
        """Get constraints for optimization based on disruption type"""
        constraints = {}

        disruption_type = disruption.get('disruption_type', '')
        entity_type = disruption.get('entity_type', '')
        entity_id = disruption.get('entity_id', '')

        # Base constraints from config
        constraints['max_cost'] = config.get_service_objective('cost_constraints', 'max_logistics_cost_per_unit') * 10  # Scale up for total cost
        constraints['max_lead_time'] = config.get_service_objective('delivery_timelines', 'max_delivery_delay_hours') / 24  # Convert hours to days
        constraints['min_reliability'] = 0.6  # Minimum acceptable reliability
        constraints['max_carbon'] = config.get_service_objective('carbon_constraints', 'max_carbon_footprint_per_shipment') * 2  # Allow some flexibility

        # Adjust based on disruption type
        if disruption_type in ['stockout', 'low_inventory']:
            constraints['max_lead_time'] = min(constraints['max_lead_time'], 7.0)  # Need faster resolution for stockouts
            constraints['min_reliability'] = max(constraints['min_reliability'], 0.7)  # Higher reliability needed
        elif disruption_type in ['delivery_delay', 'shipment_issue']:
            constraints['max_lead_time'] = min(constraints['max_lead_time'], 3.0)  # Much faster shipping needed
        elif 'vendor' in disruption_type:
            constraints['min_reliability'] = max(constraints['min_reliability'], 0.7)  # Need reliable vendors
            constraints['max_cost'] = min(constraints['max_cost'], 500.0)  # Cost conscious for vendor changes

        return constraints

    def _record_optimization_result(self, disruption: Dict[str, Any],
                                  alternatives: List[Dict[str, Any]],
                                  result: Dict[str, Any],
                                  used_tool: bool) -> None:
        """Record the optimization result"""
        try:
            # Record action in state manager
            state_manager.record_action({
                'action_type': 'optimization_completed',
                'disruption_id': disruption.get('disruption_id'),
                'alternatives_considered': len(alternatives),
                'recommended_alternative': result.get('recommended_alternative', {}).get('description', 'Unknown'),
                'optimization_method': 'external_tool' if used_tool else 'internal_algorithm',
                'alternative_score': result.get('alternative_score', 0.0),
                'timestamp': datetime.now().isoformat()
            })

            logger.info(f"Optimization completed using {'external tool' if used_tool else 'internal algorithm'}. "
                       f"Recommended: {result.get('recommended_alternative', {}).get('description', 'Unknown')}")

        except Exception as e:
            logger.error(f"Error recording optimization result: {e}")

    def _create_no_alternatives_result(self) -> Dict[str, Any]:
        """Create result when no alternatives are available"""
        return {
            'recommended_alternative': None,
            'alternative_score': 0.0,
            'score_details': {
                'error': 'No alternatives available for optimization'
            },
            'all_alternatives_scored': [],
            'optimization_method': 'internal_multi_objective',
            'timestamp': datetime.now().isoformat(),
            'weights_used': self.objective_weights.copy(),
            'total_alternatives_considered': 0
        }

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create result when optimization encounters an error"""
        return {
            'recommended_alternative': None,
            'alternative_score': 0.0,
            'score_details': {
                'error': error_message
            },
            'all_alternatives_scored': [],
            'optimization_method': 'error',
            'timestamp': datetime.now().isoformat(),
            'weights_used': self.objective_weights.copy(),
            'total_alternatives_considered': 0
        }

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current status of the optimization engine"""
        with self._queue_lock:
            queue_size = len(self._optimization_queue)

        return {
            'optimization_active': not self._stop_optimization.is_set(),
            'queue_size': queue_size,
            'last_optimization': getattr(self, '_last_optimization_time', None),
            'cached_optimizations': len(self._optimization_cache),
            'objective_weights': self.objective_weights.copy()
        }

# Global optimization engine instance
optimization_engine = OptimizationEngine()