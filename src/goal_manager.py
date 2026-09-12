"""
Goal Manager for the Autonomous Supply Chain Recovery Agent
Defines and maintains service objectives that the agent works to achieve
"""

import time
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from .config import config
from .state_manager import state_manager

class GoalManager:
    """Manages service objectives and goal progress for the supply chain recovery agent"""

    def __init__(self):
        self._objectives = self._load_objectives_from_config()
        self._goal_progress = {}  # Track progress toward each objective
        self._lock = threading.RLock()
        self._last_evaluation = time.time()

        # Initialize goal progress tracking
        self._initialize_goal_progress()

    def _load_objectives_from_config(self) -> Dict[str, Any]:
        """Load service objectives from configuration"""
        objectives = {}

        # Load inventory objectives
        inventory_obj = config.get_service_objective('inventory_levels')
        objectives['inventory_levels'] = {
            'description': 'Maintain optimal inventory levels to prevent stockouts and overstock',
            'metrics': ['safety_stock_level', 'days_of_inventory', 'stockout_incidents'],
            'targets': inventory_obj,
            'weight': 0.3  # 30% importance
        }

        # Load delivery timeline objectives
        delivery_obj = config.get_service_objective('delivery_timelines')
        objectives['delivery_timelines'] = {
            'description': 'Ensure timely delivery to meet customer expectations',
            'metrics': ['delivery_delay_hours', 'on_time_delivery_percentage'],
            'targets': delivery_obj,
            'weight': 0.25  # 25% importance
        }

        # Load cost objectives
        cost_obj = config.get_service_objective('cost_constraints')
        objectives['cost_constraints'] = {
            'description': 'Control logistics costs while maintaining service levels',
            'metrics': ['logistics_cost_per_unit', 'cost_variance'],
            'targets': cost_obj,
            'weight': 0.25  # 25% importance
        }

        # Load carbon objectives
        carbon_obj = config.get_service_objective('carbon_constraints')
        objectives['carbon_constraints'] = {
            'description': 'Minimize environmental impact of logistics operations',
            'metrics': ['carbon_footprint_per_shipment', 'carbon_reduction_rate'],
            'targets': carbon_obj,
            'weight': 0.2  # 20% importance
        }

        return objectives

    def _initialize_goal_progress(self) -> None:
        """Initialize progress tracking for each objective"""
        with self._lock:
            for obj_key in self._objectives:
                self._goal_progress[obj_key] = {
                    'current_value': 0.0,
                    'target_value': 0.0,
                    'progress_percentage': 0.0,
                    'is_met': False,
                    'last_evaluated': None,
                    'trend': 'stable'  # improving, declining, stable
                }

    def get_objectives(self) -> Dict[str, Any]:
        """Get all service objectives"""
        with self._lock:
            return json.loads(json.dumps(self._objectives))  # Deep copy

    def get_objective(self, objective_key: str) -> Dict[str, Any]:
        """Get a specific service objective"""
        with self._lock:
            if objective_key not in self._objectives:
                raise ValueError(f"Unknown objective: {objective_key}")
            return json.loads(json.dumps(self._objectives[objective_key]))  # Deep copy

    def evaluate_objective_progress(self, objective_key: str, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate progress toward a specific objective"""
        with self._lock:
            if objective_key not in self._objectives:
                raise ValueError(f"Unknown objective: {objective_key}")

            objective = self._objectives[objective_key]
            targets = objective['targets']

            # Calculate progress based on objective type
            progress_info = self._calculate_objective_progress(objective_key, targets, current_metrics)

            # Update goal progress tracking
            self._goal_progress[objective_key].update({
                'current_value': progress_info['current_value'],
                'target_value': progress_info['target_value'],
                'progress_percentage': progress_info['progress_percentage'],
                'is_met': progress_info['is_met'],
                'last_evaluated': datetime.now().isoformat(),
                'trend': progress_info['trend']
            })

            # Update state manager with compliance status
            state_manager.update_service_objective_compliance(
                objective_key,
                progress_info['is_met'],
                {
                    'current_value': progress_info['current_value'],
                    'target_value': progress_info['target_value'],
                    'progress_percentage': progress_info['progress_percentage'],
                    'details': progress_info.get('details', {})
                }
            )

            return progress_info

    def _calculate_objective_progress(self, objective_key: str, targets: Dict[str, Any],
                                    current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate progress toward a specific objective based on its type"""

        if objective_key == 'inventory_levels':
            return self._calculate_inventory_progress(targets, current_metrics)
        elif objective_key == 'delivery_timelines':
            return self._calculate_delivery_progress(targets, current_metrics)
        elif objective_key == 'cost_constraints':
            return self._calculate_cost_progress(targets, current_metrics)
        elif objective_key == 'carbon_constraints':
            return self._calculate_carbon_progress(targets, current_metrics)
        else:
            # Default calculation for unknown objectives
            return {
                'current_value': 0.0,
                'target_value': 0.0,
                'progress_percentage': 0.0,
                'is_met': False,
                'trend': 'unknown',
                'details': {'error': f'Unknown objective type: {objective_key}'}
            }

    def _calculate_inventory_progress(self, targets: Dict[str, Any],
                                    current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate inventory objective progress"""
        # Get current inventory state
        inventory_state = state_manager.get_inventory()

        # Calculate key metrics
        total_items = sum(item.get('quantity', 0) for item in inventory_state.values()) if inventory_state else 0
        safety_stock = targets.get('min_safety_stock', 10)
        max_inventory_days = targets.get('max_days_of_inventory', 30)
        reorder_point = targets.get('reorder_point', 20)

        # Simple progress calculation based on safety stock adherence
        items_below_safety = sum(1 for item in inventory_state.values()
                               if item.get('quantity', 0) < safety_stock) if inventory_state else 0
        total_products = len(inventory_state) if inventory_state else 1

        # Progress is percentage of products ABOVE safety stock
        if total_products > 0:
            progress_percentage = ((total_products - items_below_safety) / total_products) * 100
        else:
            progress_percentage = 100.0  # No products = no risk

        is_met = progress_percentage >= 80.0  # Consider met if 80%+ of products above safety stock

        # Determine trend (simplified)
        trend = 'stable'  # In a real implementation, we'd compare with previous values

        return {
            'current_value': progress_percentage,
            'target_value': 100.0,  # Target is 100% of products above safety stock
            'progress_percentage': progress_percentage,
            'is_met': is_met,
            'trend': trend,
            'details': {
                'total_products': total_products,
                'products_below_safety_stock': items_below_safety,
                'total_inventory_units': total_items,
                'safety_stock_threshold': safety_stock
            }
        }

    def _calculate_delivery_progress(self, targets: Dict[str, Any],
                                   current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate delivery timeline objective progress"""
        # Get current shipment state
        shipments = state_manager.get_shipment()

        if not shipments:
            # No shipments = perfect delivery status
            return {
                'current_value': 100.0,
                'target_value': 100.0,
                'progress_percentage': 100.0,
                'is_met': True,
                'trend': 'stable',
                'details': {'message': 'No active shipments'}
            }

        # Calculate delivery metrics
        max_delay_hours = targets.get('max_delivery_delay_hours', 24)
        on_time_target = targets.get('on_time_delivery_target', 0.95)

        on_time_shipments = 0
        total_shipments = len(shipments)
        total_delay_hours = 0.0

        for shipment in shipments.values():
            delay_hours = shipment.get('delay_hours', 0)
            total_delay_hours += delay_hours
            if delay_hours <= max_delay_hours:
                on_time_shipments += 1

        on_time_percentage = (on_time_shipments / total_shipments) * 100 if total_shipments > 0 else 100.0
        average_delay = total_delay_hours / total_shipments if total_shipments > 0 else 0.0

        # Progress is based on on-time delivery percentage
        progress_percentage = min(on_time_percentage, 100.0)  # Cap at 100%
        is_met = on_time_percentage >= (on_time_target * 100)  # Convert target to percentage

        # Update performance metrics
        state_manager.update_performance_metric('on_time_delivery_rate', on_time_percentage / 100.0)
        state_manager.update_performance_metric('average_delay_hours', average_delay)

        # Determine trend
        trend = 'stable'  # Simplified

        return {
            'current_value': on_time_percentage,
            'target_value': on_time_target * 100,
            'progress_percentage': progress_percentage,
            'is_met': is_met,
            'trend': trend,
            'details': {
                'total_shipments': total_shipments,
                'on_time_shipments': on_time_shipments,
                'average_delay_hours': average_delay,
                'max_allowed_delay_hours': max_delay_hours
            }
        }

    def _calculate_cost_progress(self, targets: Dict[str, Any],
                               current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cost objective progress"""
        # Get current performance metrics
        metrics = state_manager.get_performance_metrics()

        current_cost_per_unit = metrics.get('average_cost_per_unit', 0.0)
        max_cost_per_unit = targets.get('max_logistics_cost_per_unit', 5.0)
        cost_variance_tolerance = targets.get('cost_variance_tolerance', 0.1)

        # Calculate progress as inverse of cost ratio (lower cost = better progress)
        if current_cost_per_unit > 0:
            cost_ratio = current_cost_per_unit / max_cost_per_unit
            progress_percentage = max(0, (2 - cost_ratio) * 50)  # Invert so lower cost = higher progress
            progress_percentage = min(progress_percentage, 100.0)  # Cap at 100%
        else:
            progress_percentage = 100.0  # No cost = perfect score

        # Check if cost is within tolerance
        is_met = current_cost_per_unit <= (max_cost_per_unit * (1 + cost_variance_tolerance))

        # Update performance metrics
        state_manager.update_performance_metric('average_cost_per_unit', current_cost_per_unit)

        # Determine trend
        trend = 'stable'

        return {
            'current_value': current_cost_per_unit,
            'target_value': max_cost_per_unit,
            'progress_percentage': progress_percentage,
            'is_met': is_met,
            'trend': trend,
            'details': {
                'cost_ratio': current_cost_per_unit / max_cost_per_unit if max_cost_per_unit > 0 else 0,
                'cost_variance_tolerance': cost_variance_tolerance,
                'within_tolerance': is_met
            }
        }

    def _calculate_carbon_progress(self, targets: Dict[str, Any],
                                 current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate carbon footprint objective progress"""
        # Get current performance metrics
        metrics = state_manager.get_performance_metrics()

        current_carbon_per_shipment = metrics.get('average_carbon_per_shipment', 0.0)
        max_carbon_per_shipment = targets.get('max_carbon_footprint_per_shipment', 100.0)
        carbon_reduction_target = targets.get('carbon_reduction_target', 0.05)

        # Calculate progress based on carbon efficiency
        if current_carbon_per_shipment > 0 and max_carbon_per_shipment > 0:
            carbon_ratio = current_carbon_per_shipment / max_carbon_per_shipment
            progress_percentage = max(0, (2 - carbon_ratio) * 50)  # Invert so lower carbon = higher progress
            progress_percentage = min(progress_percentage, 100.0)  # Cap at 100%
        else:
            progress_percentage = 100.0  # No emissions = perfect score

        # Check if carbon is within target
        is_met = current_carbon_per_shipment <= max_carbon_per_shipment

        # Update performance metrics
        state_manager.update_performance_metric('average_carbon_per_shipment', current_carbon_per_shipment)

        # Determine trend
        trend = 'stable'

        return {
            'current_value': current_carbon_per_shipment,
            'target_value': max_carbon_per_shipment,
            'progress_percentage': progress_percentage,
            'is_met': is_met,
            'trend': trend,
            'details': {
                'carbon_ratio': current_carbon_per_shipment / max_carbon_per_shipment if max_carbon_per_shipment > 0 else 0,
                'max_allowed_carbon': max_carbon_per_shipment,
                'carbon_efficiency': 1.0 - (current_carbon_per_shipment / max_carbon_per_shipment) if max_carbon_per_shipment > 0 else 1.0
            }
        }

    def get_overall_goal_progress(self) -> Dict[str, Any]:
        """Get overall progress across all objectives"""
        with self._lock:
            if not self._goal_progress:
                return {
                    'overall_progress_percentage': 0.0,
                    'objectives_met': 0,
                    'total_objectives': 0,
                    'weighted_progress': 0.0,
                    'status': 'no_objectives_defined'
                }

            total_weight = sum(obj['weight'] for obj in self._objectives.values())
            weighted_progress = 0.0
            objectives_met = 0

            for obj_key, objective in self._objectives.items():
                progress = self._goal_progress[obj_key]
                weight = objective['weight'] / total_weight if total_weight > 0 else 0
                weighted_progress += progress['progress_percentage'] * weight
                if progress['is_met']:
                    objectives_met += 1

            overall_progress = min(weighted_progress, 100.0)  # Cap at 100%

            # Determine overall status
            if objectives_met == len(self._objectives):
                status = 'all_objectives_met'
            elif objectives_met >= len(self._objectives) * 0.8:
                status = 'most_objectives_met'
            elif objectives_met >= len(self._objectives) * 0.5:
                status = 'some_objectives_met'
            else:
                status = 'few_objectives_met'

            return {
                'overall_progress_percentage': overall_progress,
                'objectives_met': objectives_met,
                'total_objectives': len(self._objectives),
                'weighted_progress': weighted_progress,
                'status': status,
                'objective_details': {
                    obj_key: {
                        'progress_percentage': progress['progress_percentage'],
                        'is_met': progress['is_met'],
                        'trend': progress['trend']
                    }
                    for obj_key, progress in self._goal_progress.items()
                }
            }

    def get_objective_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for improving objective progress"""
        recommendations = []

        with self._lock:
            for obj_key, objective in self._objectives.items():
                progress = self._goal_progress[obj_key]

                if not progress['is_met'] and progress['progress_percentage'] < 80.0:
                    # Generate recommendation based on objective type
                    recommendation = self._generate_improvement_recommendation(obj_key, objective, progress)
                    if recommendation:
                        recommendations.append(recommendation)

        # Sort by priority (objectives with lowest progress first)
        recommendations.sort(key=lambda x: x['priority'])
        return recommendations

    def _generate_improvement_recommendation(self, objective_key: str,
                                           objective: Dict[str, Any],
                                           progress: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a specific improvement recommendation for an unmet objective"""

        if objective_key == 'inventory_levels':
            return {
                'objective': objective_key,
                'priority': 100 - progress['progress_percentage'],
                'recommendation': 'Increase safety stock levels or improve replenishment frequency',
                'action_type': 'inventory_adjustment',
                'suggested_actions': [
                    'Review reorder points for products below safety stock',
                    'Increase order quantities for fast-moving items',
                    'Improve demand forecasting accuracy'
                ]
            }
        elif objective_key == 'delivery_timelines':
            return {
                'objective': objective_key,
                'priority': 100 - progress['progress_percentage'],
                'recommendation': 'Address delivery delays by optimizing routes or activating backup carriers',
                'action_type': 'delivery_optimization',
                'suggested_actions': [
                    'Identify shipments with excessive delays',
                    'Investigate root causes of delays (carrier, weather, customs)',
                    'Consider expedited shipping for critical delayed shipments'
                ]
            }
        elif objective_key == 'cost_constraints':
            return {
                'objective': objective_key,
                'priority': 100 - progress['progress_percentage'],
                'recommendation': 'Reduce logistics costs through optimization and negotiation',
                'action_type': 'cost_reduction',
                'suggested_actions': [
                    'Analyze cost drivers in current logistics network',
                    'Negotiate better rates with carriers',
                    'Optimize shipment consolidation'
                ]
            }
        elif objective_key == 'carbon_constraints':
            return {
                'objective': objective_key,
                'priority': 100 - progress['progress_percentage'],
                'recommendation': 'Reduce carbon footprint through greener logistics options',
                'action_type': 'carbon_reduction',
                'suggested_actions': [
                    'Shift to lower-carbon transportation modes where possible',
                    'Optimize routes to reduce distance traveled',
                    'Consider carbon offsetting for unavoidable emissions'
                ]
            }

        return None

# Global goal manager instance
goal_manager = GoalManager()