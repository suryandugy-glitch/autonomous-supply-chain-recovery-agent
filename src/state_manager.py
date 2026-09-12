"""
State Manager for the Autonomous Supply Chain Recovery Agent
Maintains persistent task state throughout the agent's operation
"""

import json
import time
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .config import config

class StateManager:
    """Manages persistent state for the supply chain recovery agent"""

    def __init__(self, state_file: str = "supply_chain_state.json"):
        self.state_file = state_file
        self._state = self._load_state()
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._last_checkpoint = time.time()

        # Initialize state structure if empty
        self._initialize_state_if_needed()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file or return empty state"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_state(self) -> None:
        """Save current state to file"""
        with self._lock:
            # Add timestamp to state
            self._state['_last_updated'] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)

    def _initialize_state_if_needed(self) -> None:
        """Initialize state with default structure if needed"""
        with self._lock:
            if not self._state:
                self._state = {
                    'inventory': {},  # product_id -> {quantity, location, last_updated}
                    'shipments': {},  # shipment_id -> {status, origin, destination, eta, delay}
                    'vendors': {},    # vendor_id -> {reliability_score, lead_time, capacity, last_updated}
                    'demand_forecasts': {},  # product_id -> {forecasted_demand, confidence, timestamp}
                    'actions_taken': [],  # List of actions taken with timestamps and outcomes
                    'disruptions_detected': [],  # List of disruptions detected
                    'service_objectives_met': {},  # Tracking of objective compliance
                    'performance_metrics': {  # KPIs and metrics
                        'on_time_delivery_rate': 0.0,
                        'inventory_turnover': 0.0,
                        'average_delay_hours': 0.0,
                        'total_cost': 0.0,
                        'carbon_footprint': 0.0
                    },
                    'version': '1.0'
                }
                self._save_state()

    def get_state(self) -> Dict[str, Any]:
        """Get a copy of the current state"""
        with self._lock:
            return json.loads(json.dumps(self._state))  # Deep copy

    def update_inventory(self, product_id: str, inventory_data: Dict[str, Any]) -> None:
        """Update inventory information for a product"""
        with self._lock:
            if 'inventory' not in self._state:
                self._state['inventory'] = {}

            self._state['inventory'][product_id] = {
                **inventory_data,
                'last_updated': datetime.now().isoformat()
            }
            self._maybe_checkpoint()

    def get_inventory(self, product_id: str = None) -> Dict[str, Any]:
        """Get inventory information"""
        with self._lock:
            inventory = self._state.get('inventory', {})
            if product_id is None:
                return json.loads(json.dumps(inventory))  # Deep copy
            return json.loads(json.dumps(inventory.get(product_id, {})))

    def update_shipment(self, shipment_id: str, shipment_data: Dict[str, Any]) -> None:
        """Update shipment information"""
        with self._lock:
            if 'shipments' not in self._state:
                self._state['shipments'] = {}

            self._state['shipments'][shipment_id] = {
                **shipment_data,
                'last_updated': datetime.now().isoformat()
            }
            self._maybe_checkpoint()

    def get_shipment(self, shipment_id: str = None) -> Dict[str, Any]:
        """Get shipment information"""
        with self._lock:
            shipments = self._state.get('shipments', {})
            if shipment_id is None:
                return json.loads(json.dumps(shipments))  # Deep copy
            return json.loads(json.dumps(shipments.get(shipment_id, {})))

    def update_vendor(self, vendor_id: str, vendor_data: Dict[str, Any]) -> None:
        """Update vendor information"""
        with self._lock:
            if 'vendors' not in self._state:
                self._state['vendors'] = {}

            self._state['vendors'][vendor_id] = {
                **vendor_data,
                'last_updated': datetime.now().isoformat()
            }
            self._maybe_checkpoint()

    def get_vendor(self, vendor_id: str = None) -> Dict[str, Any]:
        """Get vendor information"""
        with self._lock:
            vendors = self._state.get('vendors', {})
            if vendor_id is None:
                return json.loads(json.dumps(vendors))  # Deep copy
            return json.loads(json.dumps(vendors.get(vendor_id, {})))

    def update_demand_forecast(self, product_id: str, forecast_data: Dict[str, Any]) -> None:
        """Update demand forecast for a product"""
        with self._lock:
            if 'demand_forecasts' not in self._state:
                self._state['demand_forecasts'] = {}

            self._state['demand_forecasts'][product_id] = {
                **forecast_data,
                'timestamp': datetime.now().isoformat()
            }
            self._maybe_checkpoint()

    def get_demand_forecast(self, product_id: str = None) -> Dict[str, Any]:
        """Get demand forecast information"""
        with self._lock:
            forecasts = self._state.get('demand_forecasts', {})
            if product_id is None:
                return json.loads(json.dumps(forecasts))  # Deep copy
            return json.loads(json.dumps(forecasts.get(product_id, {})))

    def record_action(self, action_data: Dict[str, Any]) -> None:
        """Record an action taken by the agent"""
        with self._lock:
            if 'actions_taken' not in self._state:
                self._state['actions_taken'] = []

            action_record = {
                **action_data,
                'timestamp': datetime.now().isoformat(),
                'action_id': f"action_{len(self._state['actions_taken']) + 1}_{int(time.time())}"
            }

            self._state['actions_taken'].append(action_record)
            self._maybe_checkpoint()

    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent actions taken by the agent"""
        with self._lock:
            actions = self._state.get('actions_taken', [])
            return json.loads(json.dumps(actions[-limit:]))  # Deep copy of last N actions

    def record_disruption(self, disruption_data: Dict[str, Any]) -> None:
        """Record a detected disruption"""
        with self._lock:
            if 'disruptions_detected' not in self._state:
                self._state['disruptions_detected'] = []

            disruption_record = {
                **disruption_data,
                'timestamp': datetime.now().isoformat(),
                'disruption_id': f"disruption_{len(self._state['disruptions_detected']) + 1}_{int(time.time())}"
            }

            self._state['disruptions_detected'].append(disruption_record)
            self._maybe_checkpoint()

    def get_recent_disruptions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent disruptions detected"""
        with self._lock:
            disruptions = self._state.get('disruptions_detected', [])
            return json.loads(json.dumps(disruptions[-limit:]))  # Deep copy of last N disruptions

    def update_service_objective_compliance(self, objective: str, is_met: bool, details: Dict[str, Any] = None) -> None:
        """Update whether a service objective is being met"""
        with self._lock:
            if 'service_objectives_met' not in self._state:
                self._state['service_objectives_met'] = {}

            self._state['service_objectives_met'][objective] = {
                'is_met': is_met,
                'last_checked': datetime.now().isoformat(),
                'details': details or {}
            }
            self._maybe_checkpoint()

    def get_service_objective_compliance(self, objective: str = None) -> Dict[str, Any]:
        """Get service objective compliance status"""
        with self._lock:
            compliance = self._state.get('service_objectives_met', {})
            if objective is None:
                return json.loads(json.dumps(compliance))  # Deep copy
            return json.loads(json.dumps(compliance.get(objective, {})))

    def update_performance_metric(self, metric_name: str, value: float) -> None:
        """Update a performance metric"""
        with self._lock:
            if 'performance_metrics' not in self._state:
                self._state['performance_metrics'] = {}

            self._state['performance_metrics'][metric_name] = value
            self._maybe_checkpoint()

    def get_performance_metrics(self) -> Dict[str, float]:
        """Get all performance metrics"""
        with self._lock:
            return json.loads(json.dumps(self._state.get('performance_metrics', {})))

    def _maybe_checkpoint(self) -> None:
        """Save state if enough time has passed since last checkpoint"""
        current_time = time.time()
        if current_time - self._last_checkpoint >= config.get_agent_param('state_checkpoint_interval'):
            self._save_state()
            self._last_checkpoint = current_time

    def save_state(self) -> None:
        """Force save of state"""
        self._save_state()
        self._last_checkpoint = time.time()

    def get_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state for logging/display"""
        with self._lock:
            return {
                'timestamp': self._state.get('_last_updated'),
                'inventory_items': len(self._state.get('inventory', {})),
                'active_shipments': len(self._state.get('shipments', {})),
                'vendors_tracked': len(self._state.get('vendors', {})),
                'demand_forecasts': len(self._state.get('demand_forecasts', {})),
                'actions_taken': len(self._state.get('actions_taken', [])),
                'disruptions_detected': len(self._state.get('disruptions_detected', [])),
                'objectives_met': sum(1 for obj in self._state.get('service_objectives_met', {}).values() if obj.get('is_met', False)),
                'total_objectives': len(self._state.get('service_objectives_met', {}))
            }

# Global state manager instance
state_manager = StateManager()