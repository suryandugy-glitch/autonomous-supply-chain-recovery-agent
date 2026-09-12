# Autonomous Supply Chain Recovery Agent
## Tech Zephyr 4.0 Agentic AI Hackathon - Problem Statement 6

### Build an autonomous supply-chain recovery agent that maintains service objectives when inventory, shipment, vendor, or demand conditions change.

## Overview

This solution implements a true agentic AI system for supply chain management that goes beyond simple automation by:
- **Goal-driven execution**: Continuously works toward maintaining service objectives (inventory levels, delivery timelines, cost constraints, carbon footprint)
- **Tool interaction**: Meaningfully interacts with simulated logistics APIs, databases, and optimization tools
- **Persistent state**: Maintains comprehensive state that evolves over time and informs decision-making
- **Action-observation-feedback loop**: Executes actions, observes results through verification, and updates state accordingly
- **Adaptation**: Replans when conditions change or actions fail, demonstrating true adaptability
- **Outcome verification**: Validates that recovery actions actually improve the situation against objectives

## Agentic Workflow

The system implements the following agentic workflow in continuous cycles:

```
Monitor → Detect → Investigate → Optimize → Execute → Verify → (Replan if needed)
```

### 1. Monitoring Module
- Continuously polls inventory/shipment/vendor/demand APIs or simulators
- Retrieves current logistics state from multiple sources
- Detects anomalies and constraint violations
- Emits disruption events when thresholds are breached

### 2. Disruption Detector
- Analyzes monitoring data against service objectives
- Identifies specific disruption types:
  - Inventory: stockouts, low inventory, excess inventory
  - Shipment: delivery delays, shipment issues (lost, damaged, customs hold)
  - Vendor: reliability degradation, lead time issues, deactivation
  - Demand: forecast uncertainty, demand spikes
- Assesses severity and impact on service objectives
- Triggers alternative investigation process

### 3. Alternative Investigator
- Queries vendor/route/allocation databases or simulators
- Retrieves feasible alternatives when disruptions occur
- Gathers data on lead times, costs, reliability, carbon footprint
- Prepares alternative options for optimization

### 4. Optimization Engine
- Uses provided optimization tools or internal algorithms to evaluate alternatives
- Considers multi-objective constraints:
  - Cost minimization (40% weight)
  - Lead time reduction (30% weight)
  - Reliability maximization (20% weight)
  - Carbon footprint minimization (10% weight)
- Ranks alternatives based on weighted service objective impact
- Recommends optimal recovery action

### 5. Action Executor
- Executes simulated recovery actions via provided endpoints
- Handles actions like:
  - Vendor substitution
  - Shipping routing changes
  - Capacity expansion
  - Internal inventory reallocation
  - Forecast improvement
  - Escalation to human supervisors
- Tracks action execution status and timing
- Reports initiation/completion of actions

### 6. Verification Module
- Validates post-action state against service objectives
- Uses verification endpoints to confirm inventory/delivery state changes
- Measures actual vs. expected impact of recovery actions
- Determines if objectives are met or if further action is needed

### 7. Replanning Trigger
- Monitors for conditions that invalidate current plan
- Detects when chosen alternatives become unavailable
- Watches for new disruptions during recovery execution
- Initiates goal re-assessment and replanning cycle

## Key Features

### True Agentic Behavior
- **Persistent State**: Comprehensive state tracking of inventory, shipments, vendors, demand forecasts, actions taken, and disruptions detected
- **Goal Orientation**: Continuous pursuit of service objectives rather than fixed sequence execution
- **Environment Interaction**: Meaningful interaction with multiple simulated tools and APIs
- **Adaptive Replanning**: System replans when conditions change or initial actions fail
- **Verification Culture**: All actions are verified to ensure they actually improve the situation

### Service Objectives Maintained
1. **Inventory Levels**: Maintain optimal inventory to prevent stockouts and overstock
2. **Delivery Timelines**: Ensure timely delivery to meet customer expectations
3. **Cost Constraints**: Control logistics costs while maintaining service levels
4. **Carbon Constraints**: Minimize environmental impact of logistics operations

### Disruption Handling Capabilities
- **Stockout Detection**: Identifies when products go out of stock
- **Shipping Delay Detection**: Identifies significantly delayed shipments
- **Vendor Reliability Monitoring**: Tracks vendor performance degradation
- **Demand Forecast Analysis**: Identifies forecast uncertainty and spikes
- **Cascading Effect Analysis**: Understands how disruptions in one area affect others

### Recovery Action Types
- **Vendor Substitution**: Switching to alternative suppliers
- **Routing Optimization**: Changing shipping routes or carriers
- **Capacity Expansion**: Activating additional supply chain capacity
- **Internal Reallocation**: Moving inventory between locations
- **Forecast Improvement**: Enhancing demand prediction accuracy
- **Human Escalation**: Involving human supervisors for complex decisions

## Architecture

### Component Structure
```
src/
├── agent_orchestrator.py      # Main workflow coordinator
├── state_manager.py           # Persistent state management
├── goal_manager.py            # Service objective management
├── monitoring.py              # Logistics environment monitoring
├── disruption_detector.py     # Disruption identification and assessment
├── alternative_investigator.py # Alternative solution discovery
├── optimization_engine.py     # Multi-objective action optimization
├── action_executor.py         # Simulated recovery action execution
├── verification_module.py     # Post-action state validation
├── replanning_trigger.py      # Adaptive replanning initiation
└── utils.py                   # Shared utility functions
```

### Data Flow
1. **Monitoring** retrieves current state from logistics APIs/simulators
2. **State Manager** updates persistent state with new data
3. **Disruption Detector** compares state against service objectives
4. **If disruption detected**:
   - **Alternative Investigator** gathers options
   - **Optimization Engine** evaluates alternatives
   - **Action Executor** implements top recommendation
   - **Verification Module** checks results
   - **State Manager** updates with post-action state
5. **If objectives not met or new disruption detected**: trigger replanning
6. **Continuous loop** maintains service objectives over time

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure you have Python 3.9+ installed

## Usage

### Running the Agent
```bash
python -m src.agent_orchestrator
```

Or to run as a module:
```bash
python src/agent_orchestrator.py
```

### Configuration
The agent can be configured through:
- Environment variables (see config.py)
- Modifying values in src/config.py
- Adjusting objective weights in optimization_engine.py

### Demonstration
A demonstration script is available:
```bash
python src/demo_script.py
```

This will simulate various disruption scenarios and show the agentic workflow in action.

## Files

### Source Code
- `src/agent_orchestrator.py` - Main workflow coordination
- `src/state_manager.py` - Persistent state management
- `src/goal_manager.py` - Service objective management
- `src/monitoring.py` - Logistics environment monitoring
- `src/disruption_detector.py` - Disruption identification
- `src/alternative_investigator.py` - Alternative solution discovery
- `src/optimization_engine.py` - Multi-objective optimization
- `src/action_executor.py` - Action execution simulation
- `src/verification_module.py` - Action verification
- `src/replanning_trigger.py` - Replanning initiation
- `src/utils.py` - Shared utility functions

### Configuration
- `requirements.txt` - Python dependencies

## Validation and Verification

To verify the agentic nature of this solution, the system demonstrates:

1. **Goal-Driven Behavior**: Logs show persistent work toward service objectives despite disruptions
2. **Tool Interaction**: All API/tool calls are logged with timestamps and outcomes
3. **State Maintenance**: State snapshots show how information evolves and informs decisions
4. **Action-Observation**: Actions are followed by verification and state updates
5. **Adaptation**: System replans when initial actions fail or conditions change
6. **Outcome Verification**: Recovery actions are verified to ensure they actually improve the situation

### Demonstration Scenarios
The demo script shows the agent handling:
- Sudden supplier failure requiring vendor substitution
- Transportation delay requiring rerouting
- Demand spike requiring inventory reallocation
- Multiple concurrent disruptions requiring prioritization

## Design Decisions

### Why This Approach Meets Agentic AI Requirements

1. **Not a Static System**: The agent continuously monitors, learns, and adapts rather than executing a fixed script
2. **Not a Simple RAG**: While it retrieves information, it actively pursues goals through action and verification
3. **Not a One-shot LLM Response**: The agent maintains state over time and executes multi-step workflows
4. **Meaningful Tool Interaction**: Each component interacts with specific simulated tools as designed in the problem statement
5. **Persistent Task State**: The State Manager maintains comprehensive logistics state that evolves
6. **Action-Feedback Loop**: Actions execute, then are verified, with results feeding back into state
7. **Replanning Capacity**: The system demonstrably replans when conditions change or actions fail
8. **Outcome Orientation**: Success is measured by actual improvement in service objectives, not just action completion

### Technology Choices
- **Python**: Selected for readability, extensive library support, and suitability for agentic workflows
- **Modular Design**: Separation of concerns makes the system understandable, testable, and extensible
- **Background Threads**: Enables concurrent monitoring and processing without blocking the main workflow
- **JSON State Persistence**: Allows for state recovery and inspection
- **Extensible Architecture**: New disruption types, actions, or optimization criteria can be added easily

## Customization and Extension

### Adding New Disruption Types
1. Add detection logic to `disruption_detector.py`
2. Add investigation logic to `alternative_investigator.py`
3. Add optimization considerations to `optimization_engine.py` if needed
4. Add verification considerations to `verification_module.py` if needed

### Adding New Action Types
1. Define the action structure in `action_executor.py`
2. Add execution logic (simulated or via endpoint)
3. Add verification logic to `verification_module.py`
4. Update optimization engine to consider the new action type

### Modifying Objectives or Weights
1. Edit `goal_manager.py` to change objective definitions
2. Adjust weights in `optimization_engine.py` objective_weights dictionary
3. Update verification thresholds in `verification_module.py` if needed

## Performance and Scalability

### Efficiency Features
- **Selective Processing**: Components only process relevant data
- **Background Operations**: Monitoring and detection run concurrently
- **Caching Mechanisms**: Reduces redundant computations
- **Batch Processing**: Where applicable, processes items in batches

### Scalability Considerations
- **Modular Design**: Components can be scaled independently
- **Stateless Services**: Most components don't retain session-specific data
- **Configurable Intervals**: Monitoring frequency can be adjusted based on needs
- **Resource Awareness**: Components respect timeouts and resource limits

## Troubleshooting

### Common Issues
- **No API Response**: Check that simulation endpoints are running or adjust to use internal simulations
- **State Not Updating**: Verify that state manager methods are being called correctly
- **Actions Not Executing**: Check the execution queue and action executor status
- **Verification Failing**: Ensure that action effects are being properly modeled in simulations

### Logs
- Console output shows real-time agent activity
- File logging available in `supply_chain_agent.log`
- Debug logging available by modifying logging levels in utils.py

## Future Enhancements

### Potential Improvements
1. **Machine Learning Integration**: Learn from historical disruption patterns
2. **Multi-agent Coordination**: Specialized agents for different disruption types
3. **Advanced Optimization**: More sophisticated constraint handling and Pareto optimization
4. **Real-world API Integration**: Connect to actual logistics APIs and systems
5. **User Interface**: Dashboard for monitoring agent performance and intervening when needed
6. **Blockchain Integration**: For immutable audit trail of all actions and decisions
7. **IoT Sensor Integration**: Real-time data from physical supply chain assets

## Contributing

This solution was developed for the Tech Zephyr 4.0 Agentic AI Hackathon, Problem Statement 6 (Smart Automation track).

For educational purposes, feel free to:
- Study the agentic workflow implementation
- Experiment with different objective weights and disruption types
- Extend the system with new capabilities
- Use as a template for other agentic AI applications

## License

MIT License - feel free to use, modify, and distribute for educational and commercial purposes.

---

**Prepared for**: Tech Zephyr 4.0 Agentic AI Hackathon  
**Problem Statement**: 6 - Autonomous Supply Chain Recovery Agent (Smart Automation Track)  
**Approach**: True Agentic AI System with Goal-driven Execution, Tool Interaction, State Maintenance, Action-Observation Feedback Loops, Adaptation, and Outcome Verification  
**Components**: 9 specialized modules working in coordinated workflow  
**Validation**: Comprehensive demonstration of agentic behaviors through logging and state tracking