"""
Demonstration Script for the Autonomous Supply Chain Recovery Agent
Shows the agentic workflow in action through simulated disruption scenarios
"""

import time
import threading
from datetime import datetime
from src.agent_orchestrator import agent_orchestrator
from src.state_manager import state_manager
from src.goal_manager import goal_manager
from src.utils import setup_logging

# Setup logger for demo
logger = setup_logging("demo")

def run_demo():
    """Run a demonstration of the agentic workflow"""
    print("=" * 80)
    print("AUTONOMOUS SUPPLY CHAIN RECOVERY AGENT - DEMONSTRATION")
    print("Tech Zephyr 4.0 Agentic AI Hackathon - Problem Statement 6")
    print("=" * 80)
    print()
    print("This demo shows the agentic workflow:")
    print("Monitor -> Detect -> Investigate -> Optimize -> Execute -> Verify -> (Replan if needed)")
    print()

    # Start the agent
    print("Starting Autonomous Supply Chain Recovery Agent...")
    agent_orchestrator.start()

    # Give it a moment to initialize
    time.sleep(2)

    print(f"Agent started at {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Show initial state
    print("INITIAL STATE:")
    state_summary = state_manager.get_state_summary()
    goal_progress = goal_manager.get_overall_goal_progress()
    print(f"  Inventory Items: {state_summary.get('inventory_items', 0)}")
    print(f"  Active Shipments: {state_summary.get('active_shipments', 0)}")
    print(f"  Vendors Tracked: {state_summary.get('vendors_tracked', 0)}")
    print(f"  Demand Forecasts: {state_summary.get('demand_forecasts', 0)}")
    print(f"  Objectives Met: {goal_progress.get('objectives_met', 0)}/{goal_progress.get('total_objectives', 0)}")
    print(f"  Overall Status: {goal_progress.get('status', 'unknown')}")
    print()

    # Demo Scenario 1: Supplier Failure (Vendor Disruption)
    print("SCENARIO 1: Sudden Supplier Failure")
    print("-" * 40)
    print("Simulating: Primary vendor for critical component goes offline")
    print()

    # We'll simulate this by triggering a vendor disruption through the state manager
    # In a real scenario, this would come from monitoring

    # Let's manually create some initial state to work with
    print("Setting up initial conditions...")

    # Add some sample data
    state_manager.update_inventory("COMPONENT_A", {
        "quantity": 50,
        "location": "Warehouse 1",
        "unit_cost": 12.50
    })

    state_manager.update_inventory("COMPONENT_B", {
        "quantity": 25,
        "location": "Warehouse 1",
        "unit_cost": 8.75
    })

    state_manager.update_shipment("SHIP_001", {
        "origin": "Supplier Factory",
        "destination": "Manufacturing Plant",
        "status": "in_transit",
        "delay_hours": 2.0,
        "eta": "2026-09-15T10:30:00Z"
    })

    state_manager.update_vendor("PRIMARY_VENDOR", {
        "name": "Primary Electronics Supplier",
        "reliability_score": 0.95,
        "lead_time_days": 7,
        "capacity_units_per_day": 100,
        "is_active": True
    })

    state_manager.update_vendor("BACKUP_VENDOR", {
        "name": "Backup Electronics Supplier",
        "reliability_score": 0.85,
        "lead_time_days": 10,
        "capacity_units_per_day": 50,
        "is_active": True
    })

    state_manager.update_demand_forecast("COMPONENT_A", {
        "forecasted_demand": 100,
        "confidence_level": 0.8,
        "forecast_period_days": 30
    })

    # Show state after setup
    state_summary = state_manager.get_state_summary()
    goal_progress = goal_manager.get_overall_goal_progress()
    print(f"  After setup - Inventory Items: {state_summary.get('inventory_items', 0)}")
    print(f"  Objectives Met: {goal_progress.get('objectives_met', 0)}/{goal_progress.get('total_objectives', 0)}")
    print()

    # Simulate a vendor disruption
    print("Injecting vendor disruption: PRIMARY_VENDOR goes offline...")
    state_manager.update_vendor("PRIMARY_VENDOR", {
        "name": "Primary Electronics Supplier",
        "reliability_score": 0.95,
        "lead_time_days": 7,
        "capacity_units_per_day": 100,
        "is_active": False  # Vendor goes offline
    })

    # Record the disruption manually for demo purposes
    disruption_data = {
        'type': 'vendor_deactivation',
        'entity_type': 'vendor',
        'entity_id': 'PRIMARY_VENDOR',
        'severity': 'high',
        'description': 'Primary vendor for critical components has gone offline',
        'impact_assessment': {
            'financial_impact': 'Loss of primary supply source',
            'operational_impact': 'Production line disruption risk',
            'service_impact': 'High - affects multiple product lines'
        }
    }
    state_manager.record_disruption(disruption_data)

    print("Disruption recorded. Agent should now:")
    print("  1. Detect the vendor deactivation (via monitoring/disruption detection)")
    print("  2. Investigate alternative vendors")
    print("  3. Optimize selection based on cost, lead time, reliability")
    print("  4. Execute vendor switch action")
    print("  5. Verify the action resolved the disruption")
    print("  6. Update goals based on verified improvement")
    print()

    # Wait for the agent to process this disruption
    print("Agent processing disruption... (waiting 15 seconds)")
    for i in range(15, 0, -1):
        print(f"  {i}...", end="", flush=True)
        time.sleep(1)
    print("\n")

    # Check what happened
    print("AFTER AGENT PROCESSING:")
    state_summary = state_manager.get_state_summary()
    goal_progress = goal_manager.get_overall_goal_progress()
    recent_actions = state_manager.get_recent_actions(10)

    print(f"  Cycle Count: {agent_orchestrator._cycle_count}")
    print(f"  Inventory Items: {state_summary.get('inventory_items', 0)}")
    print(f"  Objectives Met: {goal_progress.get('objectives_met', 0)}/{goal_progress.get('total_objectives', 0)}")
    print(f"  Overall Status: {goal_progress.get('status', 'unknown')}")
    print()

    print("Recent Actions:")
    for i, action in enumerate(recent_actions[:5], 1):
        action_type = action.get('action_type', 'unknown')
        description = action.get('description', 'No description')
        timestamp = action.get('timestamp', 'Unknown time')
        if len(timestamp) > 19:
            timestamp = timestamp[:19]
        print(f"  {i}. [{action_type}] {description} ({timestamp})")
    print()

    # Demo Scenario 2: Shipping Delay
    print("SCENARIO 2: Shipping Delay Disruption")
    print("-" * 40)
    print("Simulating: Major shipment delayed due to weather")
    print()

    # Create a delayed shipment
    state_manager.update_shipment("SHIP_002", {
        "origin": "East Coast Port",
        "destination": "West Coast Distribution",
        "status": "delayed",
        "delay_hours": 36.0,  # Significantly delayed
        "eta": "2026-09-20T14:00:00Z"
    })

    # Record disruption
    disruption_data = {
        'type': 'delivery_delay',
        'entity_type': 'shipment',
        'entity_id': 'SHIP_002',
        'severity': 'high',
        'description': 'Shipment from East Coast delayed 36 hours due to severe weather',
        'impact_assessment': {
            'financial_impact': 'Expediting costs and potential production delays',
            'operational_impact': 'Downstream process disruption',
            'service_impact': 'High - affects delivery commitments'
        }
    }
    state_manager.record_disruption(disruption_data)

    print("Shipping delay disruption recorded.")
    print("Agent should detect this and investigate alternative routing options.")
    print()

    # Wait for processing
    print("Agent processing shipping delay... (waiting 15 seconds)")
    for i in range(15, 0, -1):
        print(f"  {i}...", end="", flush=True)
        time.sleep(1)
    print("\n")

    print("AFTER SHIPPING DELAY PROCESSING:")
    state_summary = state_manager.get_state_summary()
    goal_progress = goal_manager.get_overall_goal_progress()
    recent_actions = state_manager.get_recent_actions(10)

    print(f"  Cycle Count: {agent_orchestrator._cycle_count}")
    print(f"  Objectives Met: {goal_progress.get('objectives_met', 0)}/{goal_progress.get('total_objectives', 0)}")
    print(f"  Overall Status: {goal_progress.get('status', 'unknown')}")
    print()

    print("Recent Actions:")
    for i, action in enumerate(recent_actions[:5], 1):
        action_type = action.get('action_type', 'unknown')
        description = action.get('description', 'No description')
        timestamp = action.get('timestamp', 'Unknown time')
        if len(timestamp) > 19:
            timestamp = timestamp[:19]
        print(f"  {i}. [{action_type}] {description} ({timestamp})")
    print()

    # Demo Scenario 3: Demand Spike
    print("SCENARIO 3: Demand Spike")
    print("-" * 40)
    print("Simulating: Unexpected surge in demand for popular product")
    print()

    # Update demand forecast to simulate spike
    state_manager.update_demand_forecast("COMPONENT_A", {
        "forecasted_demand": 300,  # Triple the original forecast
        "confidence_level": 0.75,
        "forecast_period_days": 30
    })

    # Record disruption
    disruption_data = {
        'type': 'demand_forecast_spike',
        'entity_type': 'product',
        'entity_id': 'COMPONENT_A',
        'severity': 'medium',
        'description': 'Unexpected demand spike for Component A - forecast tripled',
        'impact_assessment': {
            'financial_impact': 'Revenue opportunity if fulfilled, stockout risk if not',
            'operational_impact': 'Strain on production and logistics capacity',
            'service_impact': 'Medium - risk of stockouts if capacity insufficient'
        }
    }
    state_manager.record_disruption(disruption_data)

    print("Demand spike disruption recorded.")
    print("Agent should investigate capacity expansion or alternative sourcing.")
    print()

    # Wait for processing
    print("Agent processing demand spike... (waiting 15 seconds)")
    for i in range(15, 0, -1):
        print(f"  {i}...", end="", flush=True)
        time.sleep(1)
    print("\n")

    print("AFTER DEMAND SPIKE PROCESSING:")
    state_summary = state_manager.get_state_summary()
    goal_progress = goal_manager.get_overall_goal_progress()
    recent_actions = state_manager.get_recent_actions(10)

    print(f"  Cycle Count: {agent_orchestrator._cycle_count}")
    print(f"  Inventory Items: {state_summary.get('inventory_items', 0)}")
    print(f"  Objectives Met: {goal_progress.get('objectives_met', 0)}/{goal_progress.get('total_objectives', 0)}")
    print(f"  Overall Status: {goal_progress.get('status', 'unknown')}")
    print()

    print("Recent Actions:")
    for i, action in enumerate(recent_actions[:5], 1):
        action_type = action.get('action_type', 'unknown')
        description = action.get('description', 'No description')
        timestamp = action.get('timestamp', 'Unknown time')
        if len(timestamp) > 19:
            timestamp = timestamp[:19]
        print(f"  {i}. [{action_type}] {description} ({timestamp})")
    print()

    # Final Summary
    print("FINAL AGENT STATUS")
    print("-" * 40)
    final_status = agent_orchestrator.get_agent_status()

    print(f"Total Cycles Completed: {final_status['agent_orchestrator']['cycle_count']}")
    print(f"Agent Status: {final_status['agent_orchestrator']['status']}")
    if final_status['agent_orchestrator']['last_cycle_time']:
        print(f"Last Cycle: {final_status['agent_orchestrator']['last_cycle_time']}")
    print()

    print("Service Objective Progress:")
    goal_progress = final_status['goal_manager']
    print(f"  Overall: {goal_progress['status']}")
    print(f"  Objectives Met: {goal_progress['objectives_met']}/{goal_progress['total_objectives']}")
    for obj_key, obj_progress in goal_progress.get('objective_details', {}).items():
        print(f"  {obj_key}: {obj_progress['progress_percentage']:.1f}% "
              f"(Met: {obj_progress['is_met']}, Trend: {obj_progress['trend']})")
    print()

    print("State Summary:")
    state_summary = final_status['state_manager']
    print(f"  Inventory Items: {state_summary.get('inventory_items', 0)}")
    print(f"  Active Shipments: {state_summary.get('active_shipments', 0)}")
    print(f"  Vendors Tracked: {state_summary.get('vendors_tracked', 0)}")
    print(f"  Demand Forecasts: {state_summary.get('demand_forecasts', 0)}")
    print(f"  Actions Taken: {state_summary.get('actions_taken', 0)}")
    print(f"  Disruptions Detected: {state_summary.get('disruptions_detected', 0)}")
    print()

    # Stop the agent
    print("Stopping agent...")
    agent_orchestrator.stop()
    print("Demo completed!")
    print()
    print("KEY AGENTIC BEHAVIORS DEMONSTRATED:")
    print("*Goal-driven execution (continuous pursuit of service objectives)")
    print("*Tool interaction (monitoring/logistics APIs)")
    print("*Persistent state (comprehensive state tracking)")
    print("Action-observation-feedback loop (act -> verify -> update state)")
    print("*Adaptation (replanning when conditions change)")
    print("*Outcome verification (validating actions actually help)")
    print()
    print("=" * 80)

def show_code_structure():
    """Show the code structure of the agent"""
    print("\nCODE STRUCTURE:")
    print("-" * 40)
    print("src/")
    print("|-- agent_orchestrator.py      # Main workflow coordinator")
    print("|-- state_manager.py           # Persistent state management")
    print("|-- goal_manager.py            # Service objective management")
    print("|-- monitoring.py              # Logistics environment monitoring")
    print("|-- disruption_detector.py     # Disruption identification")
    print("|-- alternative_investigator.py # Alternative solution discovery")
    print("|-- optimization_engine.py     # Multi-objective action optimization")
    print("|-- action_executor.py         # Action execution simulation")
    print("|-- verification_module.py     # Action verification")
    print("|-- replanning_trigger.py      # Replanning initiation")
    print("_-- utils.py                   # Shared utility functions")
    print()
    print("KEY FILES FOR UNDERSTANDING THE AGENTIC WORKFLOW:")
    print("1. agent_orchestrator.py - Shows the main loop and coordination")
    print("2. state_manager.py - Demonstrates persistent state management")
    print("3. goal_manager.py - Shows objective-driven behavior")
    print("4. verification_module.py - Demonstrates outcome verification")
    print("5. replanning_trigger.py - Shows adaptation capabilities")

if __name__ == "__main__":
    try:
        run_demo()
        show_code_structure()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        agent_orchestrator.stop()
    except Exception as e:
        print(f"\n\nError during demo: {e}")
        agent_orchestrator.stop()