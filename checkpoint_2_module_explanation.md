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
- **Example** (subset of columns; full CSV also has `Humidity`, `Power_Consumption`):
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
- **Performance**: For large datasets the pipeline samples up to 1000 records (prioritizing rows with failures) so runs finish in reasonable time

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
- **What it means**: "This pattern preceded failure 23 times; predictive_score is a normalized frequency (min(frequency/10, 1.0))"

### Next Module Feed

**How does this output become input to Module 3?**

Module 2's outputs feed into **Module 3: Equipment Diagnosis System** (First-Order Logic):

1. **Discovered Sequences** → Module 3 uses these as **evidence** in its knowledge base
   - Example: "Sequence [A, B, C] → failure" becomes a rule: "If equipment shows pattern A→B→C, then failure is likely"
   - Module 3 can reason about these patterns using first-order logic

2. **Ranked Warning Signs** → Module 3 uses these for **prioritization**
   - Higher predictive scores indicate more urgent diagnoses
   - Module 3 can combine multiple warning signs to infer root causes

3. **Sequence and pattern structure** in the JSON (state sequences, frequencies) gives Module 3 **relational evidence** it can use in first-order logic (e.g. "pattern X often precedes failure type Y").

**Integration Point**: Module 3 will read Module 2's JSON outputs and use them as input to its knowledge base for logical inference about equipment failures.

---

## AI Concepts

### What AI techniques are used?

**1. Uninformed Search: BFS (Breadth-First Search)**
- **What it does**: Explores all states at depth 1, then depth 2, etc., using a queue
- **Why we use it**: Finds all paths from normal states to failure states systematically
- **Implementation**: `bfs()` function in `search.py` uses `collections.deque` as queue. In practice we run BFS from states that are **neighbors of failure states** (so we find paths that lead into failures).
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
- **Adaptation**: Since dataset has one record per machine, we connect states that **differ by exactly one sensor bin** (similarity-based). Each state has a cap on how many such neighbors it connects to (for performance).

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
3. **Innovation**: Similarity-based graph connections adapt to snapshot data (one record per machine)
4. **Results**: Discovered sequences and ranked warning signs (JSON outputs)
5. **Integration**: Outputs feed into Module 3 for logical diagnosis

---

## Demo Section — For Your PowerPoint

Use this section to build slides and know exactly what to show and say.

### Slide 1: Title + One-Line Goal
- **Title**: Module 2 — Failure Pattern Discovery
- **Subtitle or bullet**: "Discover sequences of sensor states that precede failures using BFS, DFS, and A*."
- **Visual**: Simple pipeline icon: Data → Graph → Search → Patterns → Output.

### Slide 2: Inputs (What the Module Accepts)
- **Headline**: Inputs
- **Three boxes or columns**:
  1. **Historical CSV**: "Machine_ID, Timestamp, sensors, Failure_Status (0/1). One row per machine."
  2. **Graph config JSON**: "Bins for Temperature, Vibration, Pressure → discrete states (low/medium/high)."
  3. **Search params JSON**: "max_depth, min_pattern_length, heuristic choice."
- **Visual**: Screenshot or mock of the CSV (first 5–6 rows) and one JSON snippet. Keep it minimal.
- **Say**: "We take timestamped sensor data with failure labels, a config that turns continuous values into bins, and search parameters."

### Slide 3: The Big Idea — Graph + Similarity
- **Headline**: Why a graph? Our data has one record per machine (no time-series per machine).
- **Visual**: 
  - Left: "Raw data → many machines, one snapshot each."
  - Right: "We build a graph: nodes = states (e.g. temp=high, vib=medium, pressure=low). Edges connect states that differ by **one** sensor bin."
- **Diagram**: 3–4 circles (states A, B, C, F). Draw edges between A–B, B–C, C–F. Mark F as "failure."
- **Say**: "We don’t have time order per machine, so we connect **similar** states. Search then finds paths that lead to failure states."

### Slide 4: Search Algorithms (BFS, DFS, A*)
- **Headline**: How we find paths: BFS, DFS, A*
- **Visual**: Three small panels or columns:
  - **BFS**: Queue, level-by-level. "Finds paths systematically; we use it from states next to failures."
  - **DFS**: Stack, go deep then backtrack. "Explores long sequences."
  - **A***: Priority queue, f = g + h. "Uses heuristics (e.g. distance to failure) to guide search."
- **Optional**: One sentence each: "Uninformed (BFS, DFS) vs informed (A*)."
- **Say**: "We run BFS from states adjacent to failures to collect paths that lead to failure; A* uses heuristics to prioritize promising paths."

### Slide 5: Outputs (What the Module Produces)
- **Headline**: Outputs
- **Two boxes**:
  1. **sequences.json**: "Lists sequences of states that precede failure, with frequency and which machines."
  2. **warning_signs.json**: "Ranked list: pattern description, predictive score, frequency."
- **Visual**: Short snippet of each JSON (3–4 lines) or a table: Pattern | Score | Frequency.
- **Say**: "We output discovered sequences and a ranked list of warning signs for downstream use."

### Slide 6: Where This Fits — Integration
- **Headline**: Integration with Module 3
- **Visual**: Simple pipeline: "Module 1 (rules) → Module 2 (patterns) → Module 3 (diagnosis)." Highlight "Module 2" and an arrow into Module 3.
- **Bullets**: "Module 3 uses sequences as evidence in its knowledge base; warning signs help prioritize diagnoses."
- **Say**: "These patterns and warning signs become input to Module 3’s first-order logic diagnosis."

### Slide 7: Live Demo or Results (If You Demo)
- **Headline**: Demo / Example results
- **Visual**: 
  - Either: Command line: `PYTHONPATH=src python3 -m equipment_monitoring.cli --module 2 --data ... --output-dir outputs/module2`
  - Or: Open `outputs/module2/sequences.json` and `warning_signs.json` and scroll to a few lines.
- **Say**: "We run the CLI with our CSV and configs; outputs appear in the given output directory."

### Slide 8: Summary + Takeaway
- **Headline**: Summary
- **Bullets**: (1) Graph from discretized states, similarity edges. (2) BFS/DFS/A* find paths to failures. (3) Outputs: sequences + ranked warning signs. (4) Feeds Module 3.
- **Say**: "Module 2 turns snapshot sensor data into a graph, uses classic search to find failure-preceding patterns, and outputs sequences and warning signs for diagnosis."

---

## Demo Script (2–3 minutes) — What to Say

1. **Show Input (≈30 s)**: "Our inputs are a CSV with machine ID, timestamp, sensors, and failure status; a graph config that defines bins; and search parameters."
2. **Graph + similarity (≈30 s)**: "Because we have one record per machine, we build a graph where we connect states that differ by one sensor bin. That lets us search for paths that lead to failure states."
3. **Search (≈30 s)**: "We use BFS from states next to failures to collect paths, and we have DFS and A* with heuristics for deeper or more guided search."
4. **Output (≈30 s)**: "We output sequences that precede failures and a ranked list of warning signs—both as JSON for Module 3."
5. **Integration (≈20 s)**: "Module 3 will use these as evidence and for prioritization in its logical diagnosis."

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
