# Module 2 Explanation - In-Person Demo Guide

**Module**: Failure Pattern Discovery  
**Checkpoint**: 2  
**Date**: February 26, 2026

---

## Module Overview

Module 2 discovers sequences of sensor changes that precede equipment failures using graph-based search algorithms. It takes historical sensor data with known failure events and uses BFS, DFS, and A* search to find patterns that predict failures.

---

## Input

### What does your module accept?

**1. Historical Sensor Data CSV** (`machine_failure_data_timestamp.csv`)
- **Format**: CSV file with columns: `Machine_ID`, `Timestamp`, `Temperature`, `Pressure`, `Vibration_Level`, `Humidity`, `Power_Consumption`, `Failure_Status`
- **Structure**: One record per machine (snapshot data, not time-series per machine)
- **Failure Label**: `Failure_Status` column (0 = normal, 1 = failure occurred)
- **Example**:
  ```csv
  Machine_ID,Timestamp,Temperature,Pressure,Vibration_Level,Failure_Status
  MACHINE_001,2025-01-01 00:00:00,56.23,106.0,3.75,0
  MACHINE_002,2025-01-01 00:10:00,36.45,179.39,8.02,0
  MACHINE_003,2025-01-01 00:20:00,64.44,432.66,4.38,1
  ```

**2. Graph Configuration JSON** (`graph_config.json`)
- **Purpose**: Defines how sensor values are discretized into states
- **Structure**: 
  ```json
  {
    "discretization": {
      "Temperature": {
        "bins": [0, 30, 50, 70, 100],
        "labels": ["low", "medium", "high", "very_high"]
      },
      "Vibration_Level": {
        "bins": [0, 3.0, 6.0, 10.0],
        "labels": ["low", "medium", "high"]
      },
      "Pressure": {
        "bins": [0, 200, 350, 500],
        "labels": ["low", "medium", "high"]
      }
    },
    "state_components": ["Temperature", "Vibration_Level", "Pressure"]
  }
  ```
- **What it does**: Converts continuous sensor values into discrete bins (e.g., temperature 56.23 → "high")

**3. Search Parameters JSON** (`search_params.json`)
- **Purpose**: Controls search algorithm behavior
- **Structure**:
  ```json
  {
    "max_depth": 50,
    "lookback_window": 50,
    "min_pattern_length": 3,
    "heuristic": "time_to_failure",
    "a_star_weight": 1.0
  }
  ```

### Constraints and Assumptions

- Historical data must contain at least some failure events (`Failure_Status=1`)
- Sensor readings must be numeric
- Dataset structure: One record per machine (we adapt by using similarity-based graph connections)

---

## Output

### What does your module produce?

**1. Discovered Sequences JSON** (`sequences.json`)
- **Purpose**: Lists sequences of sensor states that precede failures
- **Structure**:
  ```json
  {
    "sequences": [
      {
        "sequence": [
          "State(machine=MACHINE_001, bins=('medium', 'low', 'medium'))",
          "State(machine=MACHINE_001, bins=('high', 'medium', 'medium'))"
        ],
        "frequency": 15,
        "avg_time_to_failure": 2.5,
        "machines": ["MACHINE_001", "MACHINE_005", "MACHINE_012"]
      }
    ]
  }
  ```
- **What it means**: "When we see this sequence of sensor states, failure occurs 15 times"

**2. Ranked Warning Signs JSON** (`warning_signs.json`)
- **Purpose**: Warning signs sorted by predictive power
- **Structure**:
  ```json
  {
    "warning_signs": [
      {
        "pattern": "State transition: ('medium', 'low') -> ('high', 'medium') (2 steps)",
        "predictive_score": 0.92,
        "frequency": 23,
        "false_positive_rate": 0.08
      }
    ]
  }
  ```
- **What it means**: "This pattern predicts failure with 92% confidence, seen 23 times"

### Next Module Feed

**How does this output become input to Module 3?**

Module 2's outputs feed into **Module 3: Equipment Diagnosis System** (First-Order Logic):

1. **Discovered Sequences** → Module 3 uses these as **evidence** in its knowledge base
   - Example: "Sequence [A, B, C] → failure" becomes a rule: "If equipment shows pattern A→B→C, then failure is likely"
   - Module 3 can reason about these patterns using first-order logic

2. **Ranked Warning Signs** → Module 3 uses these for **prioritization**
   - Higher predictive scores indicate more urgent diagnoses
   - Module 3 can combine multiple warning signs to infer root causes

3. **Graph Structure** → Module 3 can query the graph for **state relationships**
   - "What states are similar to this failure state?"
   - "What paths lead from normal to failure?"

**Integration Point**: Module 3 will read Module 2's JSON outputs and use them as input to its knowledge base for logical inference about equipment failures.

---

## AI Concepts

### What AI techniques are used?

**1. Uninformed Search: BFS (Breadth-First Search)**
- **What it does**: Explores all states at depth 1, then depth 2, etc., using a queue
- **Why we use it**: Finds all paths from normal states to failure states systematically
- **Implementation**: `bfs()` function in `search.py` uses `collections.deque` as queue
- **Example**: Starting from state A, explores: A → [B, C] → [D, E, F] → ... until finding failure state

**2. Uninformed Search: DFS (Depth-First Search)**
- **What it does**: Explores deeply along one path before backtracking, using a stack
- **Why we use it**: Finds long sequences that lead to failures (deep exploration)
- **Implementation**: `dfs()` function in `search.py` uses list as stack with backtracking
- **Example**: Starting from state A, explores: A → B → D → ... (deep) then backtracks if no failure

**3. Informed Search: A* (A-star)**
- **What it does**: Uses heuristics to guide search toward goal, prioritizing promising paths
- **Why we use it**: Finds optimal paths to failure states efficiently
- **Implementation**: `a_star()` function uses `heapq` priority queue with `f(n) = g(n) + h(n)`
- **Heuristics**:
  - `heuristic_time_to_failure()`: Estimates time to failure
  - `heuristic_sensor_distance()`: Estimates distance in sensor space to failure states
- **Example**: Chooses paths that minimize (cost so far + estimated cost to goal)

**4. Graph Representation**
- **What it does**: Represents equipment states as graph nodes, transitions as edges
- **Why we use it**: Enables search algorithms to explore state space
- **Implementation**: `Graph` class with nodes (states), edges (transitions), failure state marking
- **Adaptation**: Since dataset has one record per machine, we connect states that differ by one sensor bin (similarity-based)

### Why these choices?

1. **BFS vs DFS**: 
   - BFS finds shortest paths (good for immediate warnings)
   - DFS finds long sequences (good for gradual degradation patterns)
   - We use both to get comprehensive coverage

2. **A* for optimization**:
   - More efficient than BFS/DFS when we have good heuristics
   - Heuristics guide search toward failures, reducing exploration
   - Demonstrates informed search understanding

3. **Graph structure**:
   - Natural representation for state transitions
   - Enables standard search algorithms
   - Similarity-based connections adapt to snapshot data structure

4. **Discretization**:
   - Converts continuous sensor values to discrete states
   - Makes graph manageable (finite states vs infinite values)
   - Enables pattern matching (same state = same pattern)

---

## Visual Explanation (For Presentation)

### Data Flow Diagram

```
Historical CSV
    ↓
[Load & Normalize]
    ↓
HistoricalRecord objects
    ↓
[Discretize Sensors]
    ↓
State objects (discrete bins)
    ↓
[Build Graph]
    ↓
Graph (nodes=states, edges=similarity)
    ↓
[Search: BFS/DFS/A*]
    ↓
Paths to failure states
    ↓
[Extract Patterns]
    ↓
Failure Sequences + Warning Signs
    ↓
JSON Outputs
```

### Graph Visualization Concept

```
Normal States          Failure States
     A ──────┐              F
     │       │              │
     B ──────┼──────→       │
     │       │              │
     C ──────┘              │
                            │
     D ────────────────────┘
```

- Nodes = equipment states (sensor bin combinations)
- Edges = states that differ by one sensor bin
- Search finds paths: A → B → C → F (failure)

### Search Algorithm Comparison

**BFS**: Explores level by level
```
Level 0: [A]
Level 1: [B, C]
Level 2: [D, E, F] ← Found failure!
```

**DFS**: Explores deep paths
```
A → B → D → ... (deep exploration)
Backtrack if no failure
```

**A***: Guided by heuristics
```
Priority Queue: [A(0+5), B(1+4), C(1+3)]
Choose C (lowest f-score)
Explore C's neighbors...
```

---

## Key Points for Demo

1. **Problem**: Find patterns that predict failures before they happen
2. **Solution**: Build graph of equipment states, search for paths to failures
3. **Innovation**: Similarity-based graph connections adapt to snapshot data
4. **Results**: Discovered sequences and ranked warning signs
5. **Integration**: Outputs feed into Module 3 for logical diagnosis

---

## Demo Script (2-3 minutes)

1. **Show Input**: Display CSV with sensor data and failure labels
2. **Explain Graph Building**: "We discretize sensors into bins, create states, connect similar states"
3. **Demonstrate Search**: "BFS explores systematically, DFS finds deep patterns, A* uses heuristics"
4. **Show Output**: Display `sequences.json` and `warning_signs.json` with real results
5. **Explain Integration**: "These patterns become evidence for Module 3's knowledge base"

---

## Questions to Anticipate

**Q: Why similarity-based connections instead of temporal?**  
A: Our dataset has one record per machine (snapshot), not time-series. Similarity connections let us find patterns across machines with similar sensor configurations.

**Q: How do you know these patterns predict failures?**  
A: We search from normal states to failure states. If a path exists, that sequence leads to failure. Frequency counts how often we see this pattern.

**Q: What if there are no failures in the data?**  
A: The module requires some failure events to discover patterns. Without failures, we can't build meaningful sequences.

**Q: How does A* heuristic work?**  
A: We estimate distance to failure states using sensor space distance or time-to-failure. This guides search toward failures more efficiently than BFS/DFS.
