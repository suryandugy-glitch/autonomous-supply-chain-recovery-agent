"""
Configuration management for the Autonomous Supply Chain Recovery Agent
"""

import os
from typing import Dict, Any

class Config:
    """Configuration class for managing agent settings"""

    def __init__(self):
        # Service objectives - what we're trying to maintain
        self.SERVICE_OBJECTIVES = {
            'inventory_levels': {
                'min_safety_stock': 10,  # Minimum units to keep in stock
                'max_days_of_inventory': 30,  # Maximum days of inventory on hand
                'reorder_point': 20  # Point at which we reorder
            },
            'delivery_timelines': {
                'max_delivery_delay_hours': 24,  # Maximum acceptable delay
                'on_time_delivery_target': 0.95  # 95% on-time delivery target
            },
            'cost_constraints': {
                'max_logistics_cost_per_unit': 5.0,  # Maximum cost per unit shipped
                'cost_variance_tolerance': 0.1  # 10% cost variance tolerance
            },
            'carbon_constraints': {
                'max_carbon_footprint_per_shipment': 100.0,  # kg CO2 per shipment
                'carbon_reduction_target': 0.05  # 5% reduction target per month
            }
        }

        
        # Tool/API endpoints (these would be provided by the hackathon sandbox)
        self.TOOL_ENDPOINTS = {
            'inventory_api': os.getenv('INVENTORY_API_URL', 'http://localhost:8000/api/inventory'),
            'shipment_api': os.getenv('SHIPMENT_API_URL', 'http://localhost:8000/api/shipments'),
            'vendor_api': os.getenv('VENDOR_API_URL', 'http://localhost:8000/api/vendors'),
            'demand_api': os.getenv('DEMAND_API_URL', 'http://localhost:8000/api/demand'),
            'optimization_tool': os.getenv('OPTIMIZATION_TOOL_URL', 'http://localhost:8000/tools/optimize'),
            'verification_endpoint': os.getenv('VERIFICATION_ENDPOINT_URL', 'http://localhost:8000/api/verify'),
            'action_endpoint': os.getenv('ACTION_ENDPOINT_URL', 'http://localhost:8000/api/actions')
        }

        # Agent behavior parameters
        self.AGENT_PARAMS = {
            'max_replanning_attempts': 3,
            'action_timeout_seconds': 300,  # 5 minutes to complete an action
            'verification_timeout_seconds': 60,  # 1 minute to verify action
            'disruption_severity_threshold': 0.7,  # Threshold for considering disruption severe
            'state_checkpoint_interval': 300,  # Save state every 5 minutes
            'monitoring_interval': 30  # Check every 30 seconds
        }

        # Logging configuration
        self.LOGGING = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': 'supply_chain_agent.log'
        }

    def get_service_objective(self, category: str, key: str = None) -> Any:
        """Get a specific service objective value"""
        if category not in self.SERVICE_OBJECTIVES:
            raise ValueError(f"Unknown service objective category: {category}")

        if key is None:
            return self.SERVICE_OBJECTIVES[category]

        if key not in self.SERVICE_OBJECTIVES[category]:
            raise ValueError(f"Unknown service objective key: {key} in category {category}")

        return self.SERVICE_OBJECTIVES[category][key]

    def get_tool_endpoint(self, tool_name: str) -> str:
        """Get endpoint for a specific tool"""
        if tool_name not in self.TOOL_ENDPOINTS:
            raise ValueError(f"Unknown tool: {tool_name}")
        return self.TOOL_ENDPOINTS[tool_name]

    def get_agent_param(self, param_name: str) -> Any:
        """Get agent parameter value"""
        if param_name not in self.AGENT_PARAMS:
            raise ValueError(f"Unknown agent parameter: {param_name}")
        return self.AGENT_PARAMS[param_name]

# Global config instance
config = Config()