"""
Basic test for the Autonomous Supply Chain Recovery Agent
Tests that components can be imported and initialized correctly
"""

def test_imports():
    """Test that all modules can be imported"""
    try:
        from src import config
        from src import state_manager
        from src import goal_manager
        from src import monitoring
        from src import disruption_detector
        from src import alternative_investigator
        from src.optimization import optimization_engine
        from src.action_executor import action_executor
        from src.verification import verification_module
        from src.replanning_trigger import replanning_trigger
        from src.agent_orchestrator import agent_orchestrator
        from src import utils

        print("[OK] All modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_initialization():
    """Test that components can be initialized"""
    try:
        from src.state_manager import state_manager
        from src.goal_manager import goal_manager
        from src.monitoring import monitoring_module
        from src.disruption_detector import disruption_detector
        from src.alternative_investigator import alternative_investigator
        from src.optimization import optimization_engine
        from src.action_executor import action_executor
        from src.verification import verification_module
        from src.replanning_trigger import replanning_trigger
        from src.agent_orchestrator import agent_orchestrator

        # Test that instances exist and have expected attributes
        assert hasattr(state_manager, 'get_state')
        assert hasattr(goal_manager, 'get_overall_goal_progress')
        assert hasattr(monitoring_module, 'start_monitoring')
        assert hasattr(disruption_detector, 'start_detection')
        assert hasattr(alternative_investigator, 'start_investigation')
        assert hasattr(optimization_engine, 'start_optimization')
        assert hasattr(action_executor, 'start_execution')
        assert hasattr(verification_module, 'start_verification')
        assert hasattr(replanning_trigger, 'start_replanning_monitoring')
        assert hasattr(agent_orchestrator, 'start')

        print("[OK] All components initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Initialization error: {e}")
        return False

def test_state_operations():
    """Test basic state manager operations"""
    try:
        from src.state_manager import state_manager

        # Test state operations
        state_manager.update_inventory("TEST_ITEM", {"quantity": 100, "location": "Test Location"})
        inventory = state_manager.get_inventory("TEST_ITEM")
        assert inventory["quantity"] == 100
        assert inventory["location"] == "Test Location"

        state_manager.record_action({"action_type": "test", "description": "Test action"})
        actions = state_manager.get_recent_actions(1)
        assert len(actions) == 1
        assert actions[0]["action_type"] == "test"

        print("[OK] State manager operations work correctly")
        return True
    except Exception as e:
        print(f"✗ State manager error: {e}")
        return False

def test_goal_operations():
    """Test basic goal manager operations"""
    try:
        from src.goal_manager import goal_manager

        # Test goal operations
        progress = goal_manager.get_overall_goal_progress()
        assert "objectives_met" in progress
        assert "total_objectives" in progress
        assert "status" in progress

        # Test objective evaluation
        test_metrics = {
            "total_inventory_units": 1000,
            "average_inventory_per_item": 50,
            "stockout_items": 0,
            "low_stock_items": 5
        }
        goal_manager.evaluate_objective_progress("inventory_levels", test_metrics)

        print("[OK] Goal manager operations work correctly")
        return True
    except Exception as e:
        print(f"✗ Goal manager error: {e}")
        return False

def main():
    """Run all tests"""
    print("Running basic tests for Autonomous Supply Chain Recovery Agent...")
    print()

    tests = [
        test_imports,
        test_initialization,
        test_state_operations,
        test_goal_operations
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[OK] All tests passed! The agent is ready to run.")
        return True
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)