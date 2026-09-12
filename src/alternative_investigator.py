"""
Alternative Investigator for the Autonomous Supply Chain Recovery Agent
Queries vendor/route/allocation databases or simulators to retrieve feasible alternatives
when disruptions occur, gathering data on lead times, costs, reliability, carbon footprint
"""

import time
import threading
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from .config import config
from .state_manager import state_manager
from .disruption_detector import disruption_detector
from .utils import setup_logging, safe_request

# Setup logger
logger = setup_logging(__name__)

class AlternativeInvestigator:
    """Investigates alternative solutions when disruptions are detected"""

    def __init__(self):
        self._investigation_thread = None
        self._stop_investigation = threading.Event()
        self._investigation_queue = []  # Queue of disruptions to investigate
        self._queue_lock = threading.Lock()
        self._last_investigation = {}
        self._investigation_cache = {}

        # Investigation intervals
        self.investigation_interval = config.get_agent_param('monitoring_interval') or 30

        # Tool endpoints
        self.endpoints = {
            'vendor': config.get_tool_endpoint('vendor_api'),
            'route': config.get_tool_endpoint('vendor_api'),  # Simplified - would be separate in reality
            'allocation': config.get_tool_endpoint('vendor_api'),  # Simplified
            'optimization_tool': config.get_tool_endpoint('optimization_tool')
        }

    def start_investigation(self) -> None:
        """Start the investigation thread"""
        if self._investigation_thread is not None and self._investigation_thread.is_alive():
            logger.warning("Alternative investigation is already running")
            return

        logger.info("Starting alternative investigation service...")
        self._stop_investigation.clear()
        self._investigation_thread = threading.Thread(target=self._investigation_loop, daemon=True)
        self._investigation_thread.start()

    def stop_investigation(self) -> None:
        """Stop the investigation thread"""
        logger.info("Stopping alternative investigation service...")
        self._stop_investigation.set()
        if self._investigation_thread:
            self._investigation_thread.join(timeout=5.0)

    def queue_disruption_for_investigation(self, disruption: Dict[str, Any]) -> None:
        """Add a disruption to the investigation queue"""
        with self._queue_lock:
            # Avoid duplicating investigations for the same disruption recently
            disruption_key = f"{disruption.get('disruption_type')}_{disruption.get('entity_type')}_{disruption.get('entity_id')}"
            last_investigated = self._last_investigation.get(disruption_key, 0)

            # Only queue if enough time has passed (5 minutes) or never investigated
            if time.time() - last_investigated > 300 or last_investigated == 0:
                self._investigation_queue.append(disruption)
                self._last_investigation[disruption_key] = time.time()
                logger.info(f"Queued disruption for investigation: {disruption.get('description')}")

    def _investigation_loop(self) -> None:
        """Main investigation loop"""
        logger.info("Investigation loop started")

        while not self._stop_investigation.is_set():
            try:
                # Process any queued disruptions
                disruption_to_investigate = None
                with self._queue_lock:
                    if self._investigation_queue:
                        disruption_to_investigate = self._investigation_queue.pop(0)

                if disruption_to_investigate:
                    self._investigate_disruption(disruption_to_investigate)
                else:
                    # No disruptions to investigate, sleep briefly
                    time.sleep(5)

            except Exception as e:
                logger.error(f"Error in investigation loop: {e}")
                time.sleep(5)  # Short sleep on error

        logger.info("Investigation loop stopped")

    def _investigate_disruption(self, disruption: Dict[str, Any]) -> None:
        """Investigate a specific disruption to find alternatives"""
        try:
            logger.info(f"Investigating disruption: {disruption.get('description')}")

            disruption_type = disruption.get('disruption_type')
            entity_type = disruption.get('entity_type')
            entity_id = disruption.get('entity_id')

            # Investigate based on disruption type
            alternatives = []

            if disruption_type in ['stockout', 'low_inventory']:
                alternatives = self._investigate_inventory_alternatives(disruption)
            elif disruption_type in ['delivery_delay', 'shipment_issue']:
                alternatives = self._investigate_shipping_alternatives(disruption)
            elif disruption_type in ['vendor_reliability_issue', 'vendor_lead_time_issue', 'vendor_deactivation']:
                alternatives = self._investigate_vendor_alternatives(disruption)
            elif disruption_type in ['demand_forecast_uncertainty', 'demand_forecast_spike']:
                alternatives = self._investigate_demand_alternatives(disruption)
            else:
                # Generic investigation
                alternatives = self._investigate_generic_alternatives(disruption)

            # If we found alternatives, pass them to the optimization engine
            if alternatives:
                self._submit_alternatives_for_optimization(disruption, alternatives)
            else:
                logger.warning(f"No alternatives found for disruption: {disruption.get('description')}")

        except Exception as e:
            logger.error(f"Error investigating disruption: {e}")

    def _investigate_inventory_alternatives(self, disruption: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Investigate alternatives for inventory-related disruptions"""
        alternatives = []

        try:
            product_id = disruption.get('entity_id')
            if not product_id:
                return alternatives

            # Get current inventory state
            inventory_state = state_manager.get_inventory()
            current_inventory = inventory_state.get(product_id, {}) if inventory_state else {}

            # Get vendor information to find alternative suppliers
            vendor_state = state_manager.get_vendor()

            # For each vendor, check if they supply this product (simplified)
            for vendor_id, vendor_data in vendor_state.items():
                if vendor_data.get('is_active', False) and vendor_data.get('reliability_score', 0) > 0.5:
                    # Simulate getting product offerings from vendor
                    product_offering = self._get_vendor_product_offering(vendor_id, product_id)
                    if product_offering:
                        alternative = {
                            'alternative_type': 'vendor_substitution',
                            'description': f'Source product {product_id} from vendor {vendor_data.get("name", vendor_id)}',
                            'vendor_id': vendor_id,
                            'vendor_name': vendor_data.get('name', vendor_id),
                            'product_id': product_id,
                            'estimated_cost': product_offering.get('unit_cost', 0.0),
                            'lead_time_days': vendor_data.get('lead_time_days', 7),
                            'reliability_score': vendor_data.get('reliability_score', 1.0),
                            'carbon_factor': vendor_data.get('cost_factor', 1.0),  # Simplified
                            'available_quantity': product_offering.get('available_quantity', 100),
                        }
                        alternatives.append(alternative)

            # Also consider internal alternatives like safety stock from other locations
            safety_stock_alternative = {
                'alternative_type': 'internal_reallocation',
                'description': f'Reallocate existing stock of product {product_id} from other locations',
                'product_id': product_id,
                'estimated_cost': 0.0,  # No additional procurement cost
                'lead_time_days': 1,  # Internal transfer
                'reliability_score': 0.9,  # High reliability for internal moves
                'carbon_factor': 0.3,  # Lower carbon for internal moves
                'available_quantity': sum(
                    inv.get('quantity', 0) for pid, inv in inventory_state.items()
                    if pid == product_id and inv.get('quantity', 0) > 10  # Only count excess
                )
            }
            if safety_stock_alternative['available_quantity'] > 0:
                alternatives.append(safety_stock_alternative)

        except Exception as e:
            logger.error(f"Error investigating inventory alternatives: {e}")

        return alternatives

    def _investigate_shipping_alternatives(self, disruption: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Investigate alternatives for shipping-related disruptions"""
        alternatives = []

        try:
            shipment_id = disruption.get('entity_id')
            if not shipment_id:
                return alternatives

            # Get current shipment state
            shipment_state = state_manager.get_shipment()
            current_shipment = shipment_state.get(shipment_id, {}) if shipment_state else {}

            origin = current_shipment.get('origin', 'unknown')
            destination = current_shipment.get('destination', 'unknown')

            # Investigate alternative routes/vendors
            vendor_state = state_manager.get_vendor()

            # Look for vendors that could handle this shipment type
            for vendor_id, vendor_data in vendor_state.items():
                if (vendor_data.get('is_active', False) and
                    vendor_data.get('reliability_score', 0) > 0.7 and
                    vendor_data.get('capacity_units_per_day', 0) > 0):

                    # Estimate shipping characteristics via this vendor
                    base_cost = 50.0  # Base shipping cost
                    distance_factor = self._estimate_distance_factor(origin, destination)

                    alternative = {
                        'alternative_type': 'carrier_substitution',
                        'description': f'Route shipment {shipment_id} via vendor {vendor_data.get("name", vendor_id)}',
                        'vendor_id': vendor_id,
                        'vendor_name': vendor_data.get('name', vendor_id),
                        'shipment_id': shipment_id,
                        'origin': origin,
                        'destination': destination,
                        'estimated_cost': base_cost * distance_factor * vendor_data.get('cost_factor', 1.0),
                        'lead_time_days': vendor_data.get('lead_time_days', 7) + 2,  # Plus handling
                        'reliability_score': vendor_data.get('reliability_score', 1.0),
                        'carbon_factor': vendor_data.get('cost_factor', 1.0) * distance_factor,
                        'capacity_available': vendor_data.get('capacity_units_per_day', 100)
                    }
                    alternatives.append(alternative)

            # Also consider expedited shipping options
            expedited_alternative = {
                'alternative_type': 'expedited_shipping',
                'description': f'Expedite shipment {shipment_id} through premium carrier',
                'shipment_id': shipment_id,
                'origin': origin,
                'destination': destination,
                'estimated_cost': current_shipment.get('estimated_cost', 100.0) * 1.5,  # 50% premium
                'lead_time_days': max(1, current_shipment.get('delay_hours', 24) / 24 * 0.5),  # Much faster
                'reliability_score': 0.95,
                'carbon_factor': 1.2,  # Expedited often means higher carbon
                'special_handling': True
            }
            alternatives.append(expedited_alternative)

        except Exception as e:
            logger.error(f"Error investigating shipping alternatives: {e}")

        return alternatives

    def _investigate_vendor_alternatives(self, disruption: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Investigate alternatives for vendor-related disruptions"""
        alternatives = []

        try:
            vendor_id = disruption.get('entity_id')
            if not vendor_id:
                return alternatives

            # Get current vendor state
            vendor_state = state_manager.get_vendor()
            current_vendor = vendor_state.get(vendor_id, {}) if vendor_state else {}

            # Look for alternative vendors with better characteristics
            for alt_vendor_id, alt_vendor_data in vendor_state.items():
                if (alt_vendor_id != vendor_id and
                    alt_vendor_data.get('is_active', False)):

                    # Calculate improvement factors
                    reliability_improvement = (
                        alt_vendor_data.get('reliability_score', 0) -
                        current_vendor.get('reliability_score', 0.5)
                    )
                    lead_time_improvement = (
                        current_vendor.get('lead_time_days', 10) -
                        alt_vendor_data.get('lead_time_days', 10)
                    )  # Negative means improvement (shorter lead time)
                    cost_improvement = (
                        current_vendor.get('cost_factor', 1.0) -
                        alt_vendor_data.get('cost_factor', 1.0)
                    )  # Negative means improvement (lower cost)

                    # Only consider if there's meaningful improvement in at least one area
                    if (reliability_improvement > 0.1 or
                        lead_time_improvement > 1 or
                        cost_improvement > 0.1):

                        alternative = {
                            'alternative_type': 'vendor_substitution',
                            'description': f'Replace vendor {current_vendor.get("name", vendor_id)} with {alt_vendor_data.get("name", alt_vendor_id)}',
                            'original_vendor_id': vendor_id,
                            'alternative_vendor_id': alt_vendor_id,
                            'alternative_vendor_name': alt_vendor_data.get('name', alt_vendor_id),
                            'reliability_score': alt_vendor_data.get('reliability_score', 1.0),
                            'lead_time_days': alt_vendor_data.get('lead_time_days', 7),
                            'cost_factor': alt_vendor_data.get('cost_factor', 1.0),
                            'capacity_units_per_day': alt_vendor_data.get('capacity_units_per_day', 100),
                            'improvements': {
                                'reliability_improvement': reliability_improvement,
                                'lead_time_improvement': lead_time_improvement,
                                'cost_improvement': cost_improvement
                            }
                        }
                        alternatives.append(alternative)

        except Exception as e:
            logger.error(f"Error investigating vendor alternatives: {e}")

        return alternatives

    def _investigate_demand_alternatives(self, disruption: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Investigate alternatives for demand-related disruptions"""
        alternatives = []

        try:
            product_id = disruption.get('entity_id')
            if not product_id:
                return alternatives

            # Get demand forecast
            demand_state = state_manager.get_demand_forecast()
            demand_data = demand_state.get(product_id, {}) if demand_state else {}

            forecasted_demand = demand_data.get('forecasted_demand', 0)
            confidence_level = demand_data.get('confidence_level', 0.5)

            # For demand spikes: investigate increasing supply capacity
            if disruption.get('disruption_type') == 'demand_forecast_spike':
                # Look for ways to increase supply
                vendor_state = state_manager.get_vendor()

                total_additional_capacity = 0
                for vendor_id, vendor_data in vendor_state.items():
                    if vendor_data.get('is_active', False):
                        # Estimate additional capacity we could activate
                        current_utilization = 0.7  # Assume 70% currently utilized
                        additional_capacity = vendor_data.get('capacity_units_per_day', 100) * (1 - current_utilization)
                        total_additional_capacity += additional_capacity

                if total_additional_capacity > 0:
                    alternative = {
                        'alternative_type': 'capacity_expansion',
                        'description': f'Increase supply capacity for product {product_id} to meet demand spike',
                        'product_id': product_id,
                        'additional_capacity_per_day': total_additional_capacity,
                        'estimated_cost_per_unit': 0.1,  # Small cost to activate capacity
                        'lead_time_days': 2,  # Time to ramp up
                        'reliability_score': 0.8,
                        'carbon_factor': 1.0
                    }
                    alternatives.append(alternative)

            # For demand uncertainty: investigate improving forecast accuracy
            elif disruption.get('disruption_type') == 'demand_forecast_uncertainty':
                alternative = {
                    'alternative_type': 'forecast_improvement',
                    'description': f'Improve demand forecasting for product {product_id} through market intelligence',
                    'product_id': product_id,
                    'target_confidence_level': 0.8,
                    'estimated_cost': 500.0,  # Cost of market research
                    'lead_time_days': 7,  # Time to gather and analyze data
                    'reliability_score': 0.9,
                    'carbon_factor': 0.1  # Minimal carbon impact
                }
                alternatives.append(alternative)

        except Exception as e:
            logger.error(f"Error investigating demand alternatives: {e}")

        return alternatives

    def _investigate_generic_alternatives(self, disruption: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Investigate generic alternatives for unspecified disruption types"""
        alternatives = []

        # Generic fallback: consider doing nothing vs. escalating to human
        alternative = {
            'alternative_type': 'escalation',
            'description': f'Escalate disruption to human supervisor for manual resolution',
            'disruption_id': disruption.get('disruption_id'),
            'estimated_cost': 0.0,
            'lead_time_days': 0,  # Immediate
            'reliability_score': 1.0,  # Humans are reliable for decisions
            'carbon_factor': 0.0,
            'requires_human_input': True
        }
        alternatives.append(alternative)

        return alternatives

    def _submit_alternatives_for_optimization(self, disruption: Dict[str, Any],
                                            alternatives: List[Dict[str, Any]]) -> None:
        """Submit discovered alternatives to the optimization engine"""
        try:
            logger.info(f"Found {len(alternatives)} alternatives for disruption, submitting for optimization")

            # Prepare optimization request
            optimization_request = {
                'disruption': disruption,
                'alternatives': alternatives,
                'timestamp': datetime.now().isoformat(),
                'request_id': f"opt_req_{int(time.time())}"
            }

            # Call optimization tool via API
            response = safe_request(
                'POST',
                self.endpoints['optimization_tool'],
                json=optimization_request,
                timeout=30
            )

            if response and response.status_code == 200:
                result = response.json()
                logger.info(f"Optimization completed successfully: {result.get('recommended_alternative', 'Unknown')}")

                # Record the optimization result
                state_manager.record_action({
                    'action_type': 'optimization_completed',
                    'disruption_id': disruption.get('disruption_id'),
                    'alternatives_considered': len(alternatives),
                    'recommended_alternative': result.get('recommended_alternative'),
                    'optimization_result': result
                })
            else:
                logger.warning(f"Optimization tool returned unsuccessful status: {response.status_code if response else 'No response'}")

        except Exception as e:
            logger.error(f"Error submitting alternatives for optimization: {e}")

    def _get_vendor_product_offering(self, vendor_id: str, product_id: str) -> Optional[Dict[str, Any]]:
        """Get what a vendor offers for a specific product (simulated)"""
        try:
            # In a real system, this would call a vendor catalog API
            # For now, we'll simulate based on vendor characteristics

            vendor_state = state_manager.get_vendor()
            vendor_data = vendor_state.get(vendor_id, {}) if vendor_state else {}

            if not vendor_data.get('is_active', False):
                return None

            # Simulate that vendors have a 60% chance of carrying any given product
            import hash
            hash_value = hash(f"{vendor_id}_{product_id}") % 100
            carries_product = hash_value < 60

            if not carries_product:
                return None

            # Generate realistic product offering
            base_cost = 10.0 + (hash(f"{vendor_id}_{product_id}_cost") % 20)  # $10-30 range
            availability = 50 + (hash(f"{vendor_id}_{product_id}_avail") % 150)  # 50-200 units

            return {
                'product_id': product_id,
                'vendor_id': vendor_id,
                'unit_cost': round(base_cost, 2),
                'available_quantity': availability,
                'lead_time_days': vendor_data.get('lead_time_days', 7),
                'reliability_score': vendor_data.get('reliability_score', 1.0)
            }

        except Exception as e:
            logger.error(f"Error getting vendor product offering: {e}")
            return None

    def _estimate_distance_factor(self, origin: str, destination: str) -> float:
        """Estimate distance factor for shipping cost calculation"""
        try:
            # Very simplified distance estimation
            # In reality, this would use GIS or distance calculation services

            # Simple hash-based distance simulation
            combined = f"{origin}_{destination}"
            hash_value = hash(combined) % 100  # 0-99

            # Convert to distance factor: 0.5 (local) to 3.0 (international)
            distance_factor = 0.5 + (hash_value / 100) * 2.5

            return max(0.5, distance_factor)  # Minimum 0.5x base cost

        except Exception as e:
            logger.error(f"Error estimating distance factor: {e}")
            return 1.0  # Default to factor of 1.0

    def get_investigation_status(self) -> Dict[str, Any]:
        """Get current status of the investigation service"""
        with self._queue_lock:
            queue_size = len(self._investigation_queue)

        return {
            'investigation_active': not self._stop_investigation.is_set(),
            'queue_size': queue_size,
            'last_investigation': getattr(self, '_last_investigation_time', None),
            'cached_investigations': len(self._investigation_cache)
        }

# Global alternative investigator instance
alternative_investigator = AlternativeInvestigator()