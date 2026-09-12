"""
Disruption Detector for the Autonomous Supply Chain Recovery Agent
Analyzes monitoring data against service objectives to identify specific types of disruptions
and assess their severity and impact on service objectives
"""

import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from .config import config
from .state_manager import state_manager
from .goal_manager import goal_manager
from .utils import setup_logging

# Setup logger
logger = setup_logging(__name__)

class DisruptionDetector:
    """Detects and assesses disruptions in the supply chain"""

    def __init__(self):
        self._detection_thread = None
        self._stop_detection = threading.Event()
        self._last_disruption_check = {}
        self._disruption_history = []
        self._assessment_cache = {}

        # Detection intervals
        self.detection_interval = config.get_agent_param('monitoring_interval') or 30

        # Disruption severity thresholds
        self.severity_thresholds = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.8
        }

    def start_detection(self) -> None:
        """Start the disruption detection thread"""
        if self._detection_thread is not None and self._detection_thread.is_alive():
            logger.warning("Disruption detection is already running")
            return

        logger.info("Starting disruption detection...")
        self._stop_detection.clear()
        self._detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self._detection_thread.start()

    def stop_detection(self) -> None:
        """Stop the disruption detection thread"""
        logger.info("Stopping disruption detection...")
        self._stop_detection.set()
        if self._detection_thread:
            self._detection_thread.join(timeout=5.0)

    def _detection_loop(self) -> None:
        """Main disruption detection loop"""
        logger.info("Disruption detection loop started")

        while not self._stop_detection.is_set():
            try:
                self._assess_current_disruptions()
                time.sleep(self.detection_interval)
            except Exception as e:
                logger.error(f"Error in disruption detection loop: {e}")
                time.sleep(5)  # Short sleep on error to prevent tight loop

        logger.info("Disruption detection loop stopped")

    def _assess_current_disruptions(self) -> None:
        """Assess current state for disruptions and their impact on objectives"""
        try:
            # Get current state
            inventory_state = state_manager.get_inventory()
            shipment_state = state_manager.get_shipment()
            vendor_state = state_manager.get_vendor()
            demand_state = state_manager.get_demand_forecast()
            recent_disruptions = state_manager.get_recent_disruptions(limit=50)

            # Assess inventory-related disruptions
            inventory_disruptions = self._assess_inventory_disruptions(inventory_state)

            # Assess shipment-related disruptions
            shipment_disruptions = self._assess_shipment_disruptions(shipment_state)

            # Assess vendor-related disruptions
            vendor_disruptions = self._assess_vendor_disruptions(vendor_state)

            # Assess demand-related disruptions
            demand_disruptions = self._assess_demand_disruptions(demand_state)

            # Combine all disruptions
            all_disruptions = inventory_disruptions + shipment_disruptions + vendor_disruptions + demand_disruptions

            # Filter out disruptions we've already assessed recently to avoid duplicate processing
            new_disruptions = self._filter_new_disruptions(all_disruptions)

            # Process each new disruption
            for disruption in new_disruptions:
                self._process_disruption(disruption)

            # Update last check time
            self._last_disruption_check['timestamp'] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Error assessing disruptions: {e}")

    def _assess_inventory_disruptions(self, inventory_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess inventory state for disruptions"""
        disruptions = []

        try:
            safety_stock = config.get_service_objective('inventory_levels', 'min_safety_stock')
            reorder_point = config.get_service_objective('inventory_levels', 'reorder_point')

            for product_id, inventory_data in inventory_state.items():
                quantity = inventory_data.get('quantity', 0)
                location = inventory_data.get('location', 'unknown')

                # Check for stockout
                if quantity <= 0:
                    disruption = self._create_disruption_record(
                        disruption_type='stockout',
                        entity_type='product',
                        entity_id=product_id,
                        severity='high',
                        description=f'Product {product_id} at {location} is out of stock',
                        current_value=quantity,
                        threshold_value=0,
                        impact_assessment=self._assess_stockout_impact(product_id, quantity),
                        recommended_actions=[
                            f'Expedite replenishment for product {product_id}',
                            f'Check for alternative suppliers of product {product_id}',
                            f'Consider demand shaping to reduce immediate need'
                        ]
                    )
                    disruptions.append(disruption)

                # Check for low inventory (below safety stock)
                elif quantity < safety_stock:
                    severity = 'medium' if quantity < (safety_stock * 0.5) else 'low'
                    disruption = self._create_disruption_record(
                        disruption_type='low_inventory',
                        entity_type='product',
                        entity_id=product_id,
                        severity=severity,
                        description=f'Product {product_id} at {location} has low inventory ({quantity} units)',
                        current_value=quantity,
                        threshold_value=safety_stock,
                        impact_assessment=self._assess_low_inventory_impact(product_id, quantity, safety_stock),
                        recommended_actions=[
                            f'Trigger replenishment order for product {product_id}',
                            f'Review safety stock levels for product {product_id}',
                            f'Check current open purchase orders for product {product_id}'
                        ]
                    )
                    disruptions.append(disruption)

                # Check for excess inventory (optional - could indicate forecasting issues)
                max_inventory = config.get_service_objective('inventory_levels', 'max_days_of_inventory') * 30  # Rough conversion
                if quantity > max_inventory and max_inventory > 0:
                    disruption = self._create_disruption_record(
                        disruption_type='excess_inventory',
                        entity_type='product',
                        entity_id=product_id,
                        severity='low',
                        description=f'Product {product_id} at {location} has excess inventory ({quantity} units)',
                        current_value=quantity,
                        threshold_value=max_inventory,
                        impact_assessment={
                            'financial_impact': 'Increased carrying costs',
                            'operational_impact': 'Reduced warehouse space availability',
                            'service_impact': 'None direct, but may indicate forecasting issues'
                        },
                        recommended_actions=[
                            f'Review demand forecast for product {product_id}',
                            f'Consider promotional activities to reduce excess inventory',
                            f'Review replenishment planning parameters'
                        ]
                    )
                    disruptions.append(disruption)

        except Exception as e:
            logger.error(f"Error assessing inventory disruptions: {e}")

        return disruptions

    def _assess_shipment_disruptions(self, shipment_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess shipment state for disruptions"""
        disruptions = []

        try:
            max_delay_hours = config.get_service_objective('delivery_timelines', 'max_delivery_delay_hours')
            on_time_target = config.get_service_objective('delivery_timelines', 'on_time_delivery_target')

            for shipment_id, shipment_data in shipment_state.items():
                status = shipment_data.get('status', '').lower()
                delay_hours = shipment_data.get('delay_hours', 0)
                origin = shipment_data.get('origin', 'unknown')
                destination = shipment_data.get('destination', 'unknown')

                # Check for significant delays
                if delay_hours > max_delay_hours:
                    severity = 'high' if delay_hours > (max_delay_hours * 2) else 'medium'
                    disruption = self._create_disruption_record(
                        disruption_type='delivery_delay',
                        entity_type='shipment',
                        entity_id=shipment_id,
                        severity=severity,
                        description=f'Shipment {shipment_id} from {origin} to {destination} delayed by {delay_hours:.1f} hours',
                        current_value=delay_hours,
                        threshold_value=max_delay_hours,
                        impact_assessment=self._assess_delay_impact(shipment_id, delay_hours, max_delay_hours),
                        recommended_actions=[
                            f'Contact carrier for shipment {shipment_id} to investigate delay cause',
                            f'Check if alternative routing is possible for shipment {shipment_id}',
                            f'Notify consignee of potential delay for shipment {shipment_id}',
                            f'Consider expediting related shipments if this is part of a larger order'
                        ]
                    )
                    disruptions.append(disruption)

                # Check for problematic statuses
                problem_indicators = ['lost', 'damaged', 'exception', 'customs_hold', 'delayed']
                if any(indicator in status for indicator in problem_indicators):
                    severity = 'high' if any(severe in status for severe in ['lost', 'damaged']) else 'medium'
                    disruption = self._create_disruption_record(
                        disruption_type='shipment_issue',
                        entity_type='shipment',
                        entity_id=shipment_id,
                        severity=severity,
                        description=f'Shipment {shipment_id} has problematic status: {status}',
                        current_value=len([ind for indicator in problem_indicators if indicator in status]),
                        threshold_value=0,
                        impact_assessment=self._assess_shipment_status_impact(shipment_id, status),
                        recommended_actions=[
                            f'Investigate cause of {status} status for shipment {shipment_id}',
                            f'Initiate tracing or recovery process for shipment {shipment_id}',
                            f'Prepare customer notification for potential delivery issues',
                            f'Check insurance coverage if shipment is lost or damaged'
                        ]
                    )
                    disruptions.append(disruption)

        except Exception as e:
            logger.error(f"Error assessing shipment disruptions: {e}")

        return disruptions

    def _assess_vendor_disruptions(self, vendor_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess vendor state for disruptions"""
        disruptions = []

        try:
            reliability_threshold = 0.7  # Below 70% reliability is concerning
            lead_time_threshold_multiplier = 2.0  # Consider it disrupted if lead time doubles

            for vendor_id, vendor_data in vendor_state.items():
                reliability_score = vendor_data.get('reliability_score', 1.0)
                lead_time_days = vendor_data.get('lead_time_days', 7)
                is_active = vendor_data.get('is_active', True)
                name = vendor_data.get('name', vendor_id)

                # Check for reliability degradation
                if reliability_score < reliability_threshold:
                    severity = 'high' if reliability_score < 0.5 else 'medium'
                    disruption = self._create_disruption_record(
                        disruption_type='vendor_reliability_issue',
                        entity_type='vendor',
                        entity_id=vendor_id,
                        severity=severity,
                        description=f'Vendor {name} ({vendor_id}) has low reliability score: {reliability_score:.2f}',
                        current_value=reliability_score,
                        threshold_value=reliability_threshold,
                        impact_assessment=self._assess_vendor_reliability_impact(vendor_id, reliability_score),
                        recommended_actions=[
                            f'Investigate root causes of poor performance for vendor {vendor_id}',
                            f'Consider reducing order volume to vendor {vendor_id} until performance improves',
                            f'Activate backup or secondary vendors for critical items',
                            f'Review contract terms and performance guarantees with vendor {vendor_id}'
                        ]
                    )
                    disruptions.append(disruption)

                # Check for excessive lead times (would need baseline to compare against)
                # For now, we'll flag very long lead times as potentially problematic
                if lead_time_days > 30:  # More than a month lead time
                    disruption = self._create_disruption_record(
                        disruption_type='vendor_lead_time_issue',
                        entity_type='vendor',
                        entity_id=vendor_id,
                        severity='low',
                        description=f'Vendor {name} ({vendor_id}) has extended lead time: {lead_time_days} days',
                        current_value=lead_time_days,
                        threshold_value=30,
                        impact_assessment={
                            'financial_impact': 'Increased safety stock requirements',
                            'operational_impact': 'Reduced supply chain responsiveness',
                            'service_impact': 'Increased risk of stockouts during demand variability'
                        },
                        recommended_actions=[
                            f'Negotiate improved lead times with vendor {vendor_id}',
                            f'Evaluate alternative vendors with better lead times',
                            f'Consider local or nearshoring options for critical items',
                            f'Increase safety stock to compensate for long lead times'
                        ]
                    )
                    disruptions.append(disruption)

                # Check for vendor deactivation
                if not is_active:
                    disruption = self._create_disruption_record(
                        disruption_type='vendor_deactivation',
                        entity_type='vendor',
                        entity_id=vendor_id,
                        severity='high',
                        description=f'Vendor {name} ({vendor_id}) has been deactivated',
                        current_value=0 if not is_active else 1,
                        threshold_value=1,
                        impact_assessment={
                            'financial_impact': 'Loss of supply source requiring replacement',
                            'operational_impact': 'Immediate disruption to supply chain',
                            'service_impact': 'High risk of stockouts for products sourced exclusively from this vendor'
                        },
                        recommended_actions=[
                            f'Immediately identify alternative sources for products from vendor {vendor_id}',
                            f'Activate emergency sourcing protocols',
                            f'Review inventory levels of products sourced from vendor {vendor_id}',
                            f'Investigate reason for vendor deactivation and potential for reactivation'
                        ]
                    )
                    disruptions.append(disruption)

        except Exception as e:
            logger.error(f"Error assessing vendor disruptions: {e}")

        return disruptions

    def _assess_demand_disruptions(self, demand_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Assess demand state for disruptions"""
        disruptions = []

        try:
            # For demand disruptions, we look for significant forecast changes or confidence issues
            # This would typically require historical comparison, but we'll do a basic check

            for product_id, demand_data in demand_state.items():
                forecasted_demand = demand_data.get('forecasted_demand', 0)
                confidence_level = demand_data.get('confidence_level', 0.5)
                forecast_period_days = demand_data.get('forecast_period_days', 30)

                # Check for low confidence forecasts
                if confidence_level < 0.3:
                    disruption = self._create_disruption_record(
                        disruption_type='demand_forecast_uncertainty',
                        entity_type='product',
                        entity_id=product_id,
                        severity='medium',
                        description=f'Low confidence in demand forecast for product {product_id}: {confidence_level:.2f}',
                        current_value=confidence_level,
                        threshold_value=0.3,
                        impact_assessment={
                            'financial_impact': 'Increased risk of overstock or stockout',
                            'operational_impact': 'Reduced effectiveness of production planning',
                            'service_impact': 'Difficulty in meeting customer service levels consistently'
                        },
                        recommended_actions=[
                            f'Review demand sensing processes for product {product_id}',
                            f'Incorporate additional market intelligence for product {product_id}',
                            f'Consider shorter forecast horizons with more frequent updates',
                            f'Engage sales and marketing teams for better demand insights'
                        ]
                    )
                    disruptions.append(disruption)

                # Check for extremely high or low forecasted demand (would need historical baseline)
                # For demonstration, we'll flag unusually high forecasts
                if forecasted_demand > 10000:  # Arbitrary high threshold
                    disruption = self._create_disruption_record(
                        disruption_type='demand_forecast_spike',
                        entity_type='product',
                        entity_id=product_id,
                        severity='medium',
                        description=f'Unusually high demand forecast for product {product_id}: {forecasted_demand} units',
                        current_value=forecasted_demand,
                        threshold_value=10000,
                        impact_assessment={
                            'financial_impact': 'Potential revenue opportunity if fulfilled',
                            'operational_impact': 'Strain on production and logistics capacity',
                            'service_impact': 'Risk of stockouts if capacity insufficient'
                        },
                        recommended_actions=[
                            f'Validate demand forecast for product {product_id} with sales team',
                            f'Assess capacity to meet increased demand for product {product_id}',
                            f'Consider phased approach to demand fulfillment',
                            f'Communicate with customers about potential delivery timelines'
                        ]
                    )
                    disruptions.append(disruption)

        except Exception as e:
            logger.error(f"Error assessing demand disruptions: {e}")

        return disruptions

    def _create_disruption_record(self, disruption_type: str, entity_type: str, entity_id: str,
                                severity: str, description: str, current_value: Any,
                                threshold_value: Any, impact_assessment: Dict[str, Any],
                                recommended_actions: List[str]) -> Dict[str, Any]:
        """Create a standardized disruption record"""
        return {
            'disruption_id': f"{disruption_type}_{entity_type}_{entity_id}_{int(time.time())}",
            'disruption_type': disruption_type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'severity': severity,
            'description': description,
            'current_value': current_value,
            'threshold_value': threshold_value,
            'impact_assessment': impact_assessment,
            'recommended_actions': recommended_actions,
            'detection_timestamp': datetime.now().isoformat(),
            'status': 'detected'  # Can be: detected, assessed, mitigated, resolved
        }

    def _assess_stockout_impact(self, product_id: str, quantity: int) -> Dict[str, Any]:
        """Assess the impact of a stockout"""
        # In a real implementation, this would look at backorders, customer impact, etc.
        return {
            'financial_impact': 'Lost sales and potential customer churn',
            'operational_impact': 'Production stoppages if used as component',
            'service_impact': 'Unable to fulfill customer orders',
            'customer_impact': 'High - direct impact on order fulfillment',
            'estimated_lost_sales_usd': 0  # Would be calculated based on product value and demand
        }

    def _assess_low_inventory_impact(self, product_id: str, quantity: int, safety_stock: int) -> Dict[str, Any]:
        """Assess the impact of low inventory"""
        stockout_risk = max(0, (safety_stock - quantity) / safety_stock) if safety_stock > 0 else 0
        return {
            'financial_impact': 'Increased expediting costs if stockout occurs',
            'operational_impact': 'May require production scheduling changes',
            'service_impact': f'Risk of stockout: {stockout_risk:.1%}',
            'customer_impact': 'Medium - potential for delayed orders',
            'stockout_risk_percentage': stockout_risk * 100
        }

    def _assess_delay_impact(self, shipment_id: str, delay_hours: float, max_delay_hours: float) -> Dict[str, Any]:
        """Assess the impact of a delivery delay"""
        delay_severity = min(delay_hours / max_delay_hours, 2.0) if max_delay_hours > 0 else 0  # Cap at 2x for scoring
        return {
            'financial_impact': f'Increased logistics costs due to expediting: ~{delay_hours * 10} USD',
            'operational_impact': 'May disrupt downstream processes dependent on this shipment',
            'service_impact': f'Delay severity: {delay_severity:.1f}x acceptable threshold',
            'customer_impact': 'Medium to High depending on delay length and customer sensitivity',
            'delay_hours': delay_hours,
            'percentage_over_threshold': ((delay_hours - max_delay_hours) / max_delay_hours * 100) if delay_hours > max_delay_hours else 0
        }

    def _assess_shipment_status_impact(self, shipment_id: str, status: str) -> Dict[str, Any]:
        """Assess the impact of a problematic shipment status"""
        status_impacts = {
            'lost': {
                'financial_impact': 'Value of goods lost plus replacement cost',
                'operational_impact': 'Complete disruption of supply chain for these goods',
                'service_impact': 'Unable to fulfill customer orders',
                'customer_impact': 'High - order cannot be fulfilled as promised'
            },
            'damaged': {
                'financial_impact': 'Value of damaged goods plus inspection/repair costs',
                'operational_impact': 'May require quarantining and inspection processes',
                'service_impact': 'Potential for partial fulfillment or delays',
                'customer_impact': 'Medium to High depending on extent of damage'
            },
            'exception': {
                'financial_impact': 'Investigation and potential resolution costs',
                'operational_impact': 'Requires manual intervention and tracking',
                'service_impact': 'Delay likely, extent depends on resolution time',
                'customer_impact': 'Low to Medium depending on delay duration'
            },
            'customs_hold': {
                'financial_impact': 'Storage fees and potential duties/taxes',
                'operational_impact': 'Supply chain paused until clearance',
                'service_impact': 'Delay dependent on customs processing time',
                'customer_impact': 'Medium - delay in international shipments'
            },
            'delayed': {
                'financial_impact': 'Potential expediting costs to recover schedule',
                'operational_impact': 'May require rescheduling of dependent activities',
                'service_impact': 'Delay in delivery timeline',
                'customer_impact': 'Low to Medium depending on delay length'
            }
        }

        # Find the most specific matching status
        for key, impact in status_impacts.items():
            if key in status:
                return impact

        # Default impact for unknown statuses
        return {
            'financial_impact': 'Unknown - requires investigation',
            'operational_impact': 'Unknown - requires investigation',
            'service_impact': 'Unknown - requires investigation',
            'customer_impact': 'Unknown - requires investigation'
        }

    def _assess_vendor_reliability_impact(self, vendor_id: str, reliability_score: float) -> Dict[str, Any]:
        """Assess the impact of vendor reliability issues"""
        failure_risk = 1.0 - reliability_score
        return {
            'financial_impact': f'Increased costs due to {failure_risk:.1%} failure rate (expediting, scrap, rework)',
            'operational_impact': f'Unreliable supply affecting production scheduling confidence',
            'service_impact': f'Risk of stockouts or quality issues: {failure_risk:.1%}',
            'customer_impact': 'Medium - potential for inconsistent product availability or quality',
            'failure_risk_percentage': failure_risk * 100
        }

    def _filter_new_disruptions(self, disruptions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out disruptions we've already processed recently"""
        new_disruptions = []
        current_time = time.time()
        cache_timeout = 300  # 5 minutes

        for disruption in disruptions:
            # Create a key for caching based on disruption characteristics
            disruption_key = f"{disruption['disruption_type']}_{disruption['entity_type']}_{disruption['entity_id']}"

            # Check if we've seen this disruption recently
            last_seen = self._disruption_history.get(disruption_key, 0)
            if current_time - last_seen > cache_timeout:
                # This is a new disruption or enough time has passed
                new_disruptions.append(disruption)
                self._disruption_history[disruption_key] = current_time

        return new_disruptions

    def _process_disruption(self, disruption: Dict[str, Any]) -> None:
        """Process a detected disruption"""
        try:
            logger.warning(f"Processing disruption: {disruption['description']}")

            # Record the disruption in state manager
            state_manager.record_disruption({
                'type': disruption['disruption_type'],
                'entity_type': disruption['entity_type'],
                'entity_id': disruption['entity_id'],
                'severity': disruption['severity'],
                'description': disruption['description'],
                'impact_assessment': disruption['impact_assessment']
            })

            # Update goal manager to reflect potential impact on objectives
            self._update_goals_for_disruption(disruption)

            # In a full implementation, this would trigger the alternative investigator
            # For now, we just log and record

        except Exception as e:
            logger.error(f"Error processing disruption: {e}")

    def _update_goals_for_disruption(self, disruption: Dict[str, Any]) -> None:
        """Update goal progress based on a detected disruption"""
        try:
            # Map disruption types to affected objectives
            disruption_objective_map = {
                'stockout': ['inventory_levels', 'delivery_timelines'],
                'low_inventory': ['inventory_levels'],
                'excess_inventory': ['inventory_levels', 'cost_constraints'],
                'delivery_delay': ['delivery_timelines', 'cost_constraints'],
                'shipment_issue': ['delivery_timelines'],
                'vendor_reliability_issue': ['inventory_levels', 'delivery_timelines', 'cost_constraints'],
                'vendor_lead_time_issue': ['inventory_levels', 'cost_constraints'],
                'vendor_deactivation': ['inventory_levels', 'delivery_timelines', 'cost_constraints'],
                'demand_forecast_uncertainty': ['inventory_levels', 'cost_constraints'],
                'demand_forecast_spike': ['inventory_levels', 'delivery_timelines']
            }

            affected_objectives = disruption_objective_map.get(
                disruption['disruption_type'],
                ['inventory_levels']  # Default
            )

            # For each affected objective, get current metrics and re-evaluate
            for objective in affected_objectives:
                # Get current state relevant to this objective
                current_metrics = self._get_objective_relevant_metrics(objective)

                # Re-evaluate progress toward this objective
                goal_manager.evaluate_objective_progress(objective, current_metrics)

        except Exception as e:
            logger.error(f"Error updating goals for disruption: {e}")

    def _get_objective_relevant_metrics(self, objective: str) -> Dict[str, Any]:
        """Get metrics relevant to a specific objective"""
        metrics = {}

        if objective == 'inventory_levels':
            inventory_state = state_manager.get_inventory()
            if inventory_state:
                quantities = [item.get('quantity', 0) for item in inventory_state.values()]
                metrics.update({
                    'total_inventory_units': sum(quantities),
                    'average_inventory_per_item': sum(quantities) / len(quantities) if quantities else 0,
                    'items_below_safety_stock': sum(1 for q in quantities if q < 10),  # Assuming safety stock of 10
                    'stockout_items': sum(1 for q in quantities if q <= 0)
                })

        elif objective == 'delivery_timelines':
            shipment_state = state_manager.get_shipment()
            if shipment_state:
                delays = [item.get('delay_hours', 0) for item in shipment_state.values()]
                on_time_shipments = sum(1 for d in delays if d <= 24)  # Assuming 24h max delay
                metrics.update({
                    'average_delay_hours': sum(delays) / len(delays) if delays else 0,
                    'on_time_shipment_percentage': (on_time_shipments / len(delays) * 100) if delays else 100,
                    'max_delay_hours': max(delays) if delays else 0,
                    'total_shipments': len(shipment_state)
                })

        elif objective == 'cost_constraints':
            # Would get actual cost data from financial systems
            # For now, use placeholders
            metrics.update({
                'estimated_logistics_cost_per_unit': 4.5,  # Placeholder
                'cost_variance': 0.05  # Placeholder
            })

        elif objective == 'carbon_constraints':
            # Would get actual carbon data from sustainability systems
            # For now, use placeholders
            metrics.update({
                'estimated_carbon_per_shipment': 85.0,  # Placeholder kg CO2
                'carbon_reduction_rate': 0.02  # Placeholder
            })

        return metrics

    def get_active_disruptions(self, severity_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get currently active disruptions"""
        try:
            # Get recent disruptions from state manager
            recent_disruptions = state_manager.get_recent_disruptions(limit=100)

            # Filter by severity if specified
            if severity_filter:
                recent_disruptions = [
                    d for d in recent_disruptions
                    if d.get('severity') == severity_filter
                ]

            # Return only disruptions that are still active (not resolved/mitigated)
            active_disruptions = [
                d for d in recent_disruptions
                if d.get('status') in ['detected', 'assessed']
            ]

            return active_disruptions

        except Exception as e:
            logger.error(f"Error getting active disruptions: {e}")
            return []

    def get_disruption_summary(self) -> Dict[str, Any]:
        """Get a summary of disruption detection activity"""
        try:
            recent_disruptions = state_manager.get_recent_disruptions(limit=50)

            # Count by severity
            severity_counts = {'low': 0, 'medium': 0, 'high': 0}
            type_counts = {}

            for disruption in recent_disruptions:
                severity = disruption.get('severity', 'unknown')
                disruption_type = disruption.get('type', 'unknown')

                if severity in severity_counts:
                    severity_counts[severity] += 1

                type_counts[disruption_type] = type_counts.get(disruption_type, 0) + 1

            return {
                'total_recent_disruptions': len(recent_disruptions),
                'severity_breakdown': severity_counts,
                'type_breakdown': type_counts,
                'last_assessment': self._last_disruption_check.get('timestamp'),
                'detection_active': not self._stop_detection.is_set() if hasattr(self, '_stop_detection') else False
            }

        except Exception as e:
            logger.error(f"Error getting disruption summary: {e}")
            return {'error': str(e)}

# Global disruption detector instance
disruption_detector = DisruptionDetector()