## Industrial Equipment Monitoring & Predictive Maintenance System

This project implements an industrial equipment monitoring and predictive maintenance system for motors, pumps, and bearings using sensor data (temperature, vibration, pressure). The system is organized into modules that correspond to core AI topics from CSC-343.

The implementation language is **Python**, with **pytest** for testing.

---

## Module Plan

The overall module plan is adapted from `PROPOSAL.md`:

| Module | Topic(s) | Inputs | Outputs | Depends On | Checkpoint |
| ------ | -------- | ------ | ------- | ---------- | ---------- |
| 1 | Propositional Logic | Configuration file (JSON), Sensor readings CSV, Equipment specifications (JSON) | Per-reading classification (JSON), Alert messages (text) | None | Checkpoint 1 (Week 3) |
| 2 | Uninformed Search (BFS, DFS), Informed Search (A*, Heuristics) | Historical sensor data with failure events, Graph structure, Search parameters | Discovered failure sequences, Visualizations, Ranked warning signs | Module 1 | Checkpoint 2 (Week 5) |
| 3 | First-Order Logic (Quantifiers, Unification, Inference) | Knowledge base, Equipment state and sensor readings, Detected anomalies | Inferred diagnosis with confidence, Explanation chains, Priority ranking, Inspection recommendations | Modules 1-2 | Checkpoint 3 (Week 7) |
| 4 | Advanced Search (Hill Climbing, Simulated Annealing), Game Theory (Minimax, Nash Equilibrium) | Equipment health assessments, Maintenance actions, Production schedule, Cost parameters | Optimized maintenance schedule, Trade-off analysis, Contingency plans | Modules 1-3 | Checkpoint 4 (Week 9) |
| 5 | Supervised Learning (Logistic Regression, Evaluation Metrics, Neural Networks) | Labeled dataset, Feature engineering pipeline, Training parameters | Trained model with metrics, Confusion matrix, Real-time predictions, Performance comparison | Modules 1-4 | Checkpoint 5 (Week 11) |
| 6 | Reinforcement Learning (MDP, Q-Learning, Policy Functions) | Environment state, Reward function, Historical feedback data | Learned policy, Adaptation history, Performance metrics | Modules 1-5 | Checkpoint 6 (Week 13) |

---

## Module 1: Basic Rule-Based Monitoring

- **Topic:** Propositional Logic (knowledge bases, inference methods)
- **Goal:** For each sensor reading, classify the equipment status as **normal** or **anomaly**, list violated rules, and provide a confidence score. Also generate human-readable alert summaries.

### Inputs

- **Configuration JSON** (global thresholds per metric)
  - Example shape:

```json
{
  "temperature": { "min": 20.0, "max": 80.0 },
  "vibration":  { "max": 5.0 },
  "pressure":   { "min": 10.0, "max": 50.0 }
}
```

- **Equipment specification JSON** (per equipment type ranges and metadata)

```json
{
  "pump_A": {
    "temperature": { "min": 25.0, "max": 75.0 },
    "vibration":  { "max": 4.5 },
    "pressure":   { "min": 12.0, "max": 45.0 }
  }
}
```

- **Sensor readings CSV**
  - Required columns for Module 1: `timestamp, equipment_id, temperature, vibration, pressure`
  - The rule engine derives which sensors to check from the configuration and equipment-spec JSON files, so adding new numeric sensors in the future is as simple as:
    - adding them (with thresholds) to the config/specs JSON, and
    - adding matching columns to the CSV.
  - Example:

```text
timestamp,equipment_id,temperature,vibration,pressure
2026-01-01T00:00:00Z,pump_A,30.0,2.1,20.0
2026-01-01T00:01:00Z,pump_A,85.0,5.5,8.0
```

### Outputs

- **Per-reading JSON classification records** (one per CSV row), e.g.:

```json
{
  "timestamp": "2026-01-01T00:01:00Z",
  "equipment_id": "pump_A",
  "status": "anomaly",
  "violated_rules": ["temperature_high", "pressure_low", "vibration_high"],
  "confidence": 0.9
}
```

- **Alert messages (text)**
  - Example line-oriented format:

```text
[2026-01-01T00:01:00Z] pump_A anomaly: temperature_high, pressure_low, vibration_high (confidence=0.90)
```

### Assumptions

- Timestamps are ISO-8601 strings in UTC.
- Units:
  - Temperature in °C.
  - Vibration as a scalar magnitude (e.g., mm/s).
  - Pressure in bar (or a consistent single unit you choose and document).
- Missing values:
  - By default, a missing sensor reading for a metric will be treated as **no reading** and can optionally trigger a `missing_<metric>` rule.
- Configuration JSON provides defaults; equipment-spec JSON can override per-equipment thresholds.
- Confidence is a **heuristic severity indicator**, not a calibrated probability. More independent rule violations generally produce higher anomaly confidence, while the presence of `missing_*` rules reduces confidence to reflect data quality concerns.

### Public Interfaces (for later modules)

These interfaces will be defined under `src/equipment_monitoring/module1/`:

- `classify_reading(reading, config, specs) -> dict`
  - Classify a single reading dict into the JSON structure above.
- `run_module1(config_path, specs_path, csv_path, output_dir) -> None`
  - End-to-end runner used by the CLI and integration tests.

---

## Module 2: Failure Pattern Discovery

- **Topic:** Uninformed Search (BFS, DFS), Informed Search (A*, Heuristics)
- **Goal:** Discover sequences of sensor changes that precede failures using graph-based search algorithms. Produce failure sequences with frequency and timing statistics, optional visualizations of degradation over time, and a ranked list of warning signs sorted by predictive power.

### Inputs

- **Historical sensor data CSV** with known failure events
  - **Primary dataset:** `machine_failure_data_timestamp.csv`
    - Required columns: `Timestamp` (datetime), `Machine_ID`, `Failure_Status` (0/1), sensor columns (Temperature, Pressure, Vibration_Level, Humidity, Power_Consumption)
    - **Note:** This dataset contains one record per machine (snapshot data), not time-series per machine. The graph connects states that differ by one sensor bin to enable pattern discovery.
  - **Secondary datasets** (adapters will be added):
    - `MAINTENANCE PREDICTIVE FOR INDUSTRIAL MACHINES.csv` (uses `Runtime` for ordering)
    - `machine failure.csv` / `ai4i2020.csv` (uses row order or Product ID runs)
  - Example structure:

```text
Machine_ID,Timestamp,Temperature,Pressure,Vibration_Level,Failure_Status
MACHINE_001,2025-01-01 00:00:00,56.23,106.0,3.75,0
MACHINE_002,2025-01-01 00:10:00,36.45,179.39,8.02,0
MACHINE_003,2025-01-01 00:20:00,64.44,432.66,4.38,1
```

- **Graph configuration JSON** (defines how sensor readings are discretized into states)
  - Example shape:

```json
{
  "discretization": {
    "temperature": { "bins": [0, 25, 50, 75, 100], "labels": ["low", "medium", "high", "very_high"] },
    "vibration": { "bins": [0, 2.5, 5.0, 7.5], "labels": ["low", "medium", "high"] },
    "pressure": { "bins": [0, 15, 30, 45], "labels": ["low", "medium", "high"] }
  }
}
```

- **Search parameters JSON** (controls search behavior)
  - Example shape:

```json
{
  "max_depth": 50,
  "lookback_window": 50,
  "min_pattern_length": 3,
  "heuristic": "time_to_failure"
}
```

### Outputs

- **Discovered sequences JSON** (sequences that precede failures)
  - Example structure:

```json
{
  "sequences": [
    {
      "sequence": ["state_A", "state_B", "state_C"],
      "frequency": 15,
      "avg_time_to_failure": 2.5,
      "machines": ["machine_001", "machine_005", "machine_012"]
    }
  ]
}
```

- **Ranked warning signs JSON** (sorted by predictive power)
  - Example structure:

```json
{
  "warning_signs": [
    {
      "pattern": "vibration rising over 3 steps",
      "predictive_score": 0.92,
      "frequency": 23,
      "false_positive_rate": 0.08
    }
  ]
}
```

- **Optional visualizations** (degradation over time plots)
  - One plot per machine showing state transitions over time with failure points marked
  - Saved as PNG files in the output directory

### Assumptions

- Historical data contains at least some failure events (`Failure_Status=1`) to discover patterns
- Sensor readings are numeric and can be discretized into bins
- **Graph building approach**: Since the dataset has one record per machine (not time-series), the graph connects states that differ by exactly one sensor bin. This allows search algorithms to find paths from normal states to failure states by exploring similar sensor configurations.
- Graph states are defined by discretized sensor combinations (binning approach)
- Search algorithms explore paths leading to failure states using BFS/DFS from states adjacent to failures
- A* heuristic uses time-to-failure or sensor-space distance to known failure regions

### Public Interfaces (for later modules)

These interfaces will be defined under `src/equipment_monitoring/module2/`:

- `load_historical_data(csv_path, config) -> List[HistoricalRecord]`
  - Load and normalize historical CSV into canonical record format
- `build_graph(records, graph_config) -> Graph`
  - Build graph structure from historical records with discretized states
- `discover_patterns(graph, search_params) -> Tuple[List[Sequence], List[WarningSign]]`
  - Run BFS/DFS and A* search to discover failure sequences and rank warning signs
- `run_module2(data_path, graph_config_path, search_params_path, output_dir) -> None`
  - End-to-end runner used by the CLI and integration tests

---

## Repository Layout

The repository is organized as follows:

```text
project-2-ai-system-casebrodee/
├── src/                      # main Python source code
├── unit_tests/               # pytest unit tests (parallel to src/)
├── integration_tests/        # integration / end-to-end tests
├── .claude/                  # agent skills
├── AGENTS.md                 # LLM agent instructions
└── README.md                 # this file
```

Module 1 code lives in `src/equipment_monitoring/module1/` with matching tests in `unit_tests/module1/`.
Module 2 code lives in `src/equipment_monitoring/module2/` with matching tests in `unit_tests/module2/`.

---

## Environment & Setup

- **Python version:** 3.10+ (recommended)

### Installing dependencies

1. Create and activate a virtual environment (example using `venv`):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

The initial dependencies are:

- `pytest` — testing framework.

Additional dependencies for future modules (e.g., plotting, ML libraries) can be added later.

---

## Running Modules

### Module 1

Run Module 1 via the CLI:

```bash
python -m equipment_monitoring.cli --module 1 \
  --config data/module1/config.json \
  --specs data/module1/equipment_specs.json \
  --readings data/module1/readings.csv \
  --output-dir outputs/module1
```

Expected outputs:

- `outputs/module1/classifications.jsonl` — one JSON record per line.
- `outputs/module1/alerts.txt` — human-readable alerts.

### Module 2

Run Module 2 via the CLI:

```bash
python -m equipment_monitoring.cli --module 2 \
  --data src/data/machine_failure_data_timestamp.csv \
  --graph-config src/data/module2/graph_config.json \
  --search-params src/data/module2/search_params.json \
  --output-dir outputs/module2
```

Expected outputs:

- `outputs/module2/sequences.json` — discovered failure sequences with frequency statistics.
- `outputs/module2/warning_signs.json` — ranked warning signs sorted by predictive power.

---

## Testing

### Unit Tests (`unit_tests/`)

Unit tests mirror the structure of `src/`. 

**Module 1:**
- `unit_tests/module1/test_config.py` - Configuration loading and validation
- `unit_tests/module1/test_rules.py` - Rule detection and violation handling
- `unit_tests/module1/test_classifier.py` - End-to-end classification
- `unit_tests/module1/test_io.py` - CSV reading and output writing

**Module 2:**
- `unit_tests/module2/test_io.py` - Historical data loading and canonical format
- `unit_tests/module2/test_graph.py` - Graph building and state discretization
- `unit_tests/module2/test_search.py` - BFS, DFS, and A* search algorithms
- `unit_tests/module2/test_patterns.py` - Sequence extraction and warning sign ranking

### Integration Tests (`integration_tests/`)

**Module 1:**
- `integration_tests/module1/test_module1_smoke.py` - Full pipeline smoke test

**Module 2:**
- `integration_tests/module2/test_module2_smoke.py` - Full pipeline smoke test on timestamped dataset

### Running Tests

Run all tests:
```bash
pytest unit_tests/ integration_tests/ -v
```

Run Module 2 tests only:
```bash
pytest unit_tests/module2/ integration_tests/module2/ -v
```

---

## Checkpoint Log

Progress tracking against course checkpoints:

| Checkpoint | Date | Modules Included | Status | Evidence |
| ---------- | ---- | ---------------- | ------ | -------- |
| 1 | Completed: Wednesday, Feb 11, 2026 | Module 1 | ✅ Complete | Module 1 fully implemented with unit and integration tests. CLI working, outputs generated. |
| 2 | Due: Thursday, Feb 26, 2026 | Module 2 | ✅ Complete | Module 2 fully implemented: graph building, BFS/DFS/A* search, pattern extraction, warning sign ranking. All tests passing. |
| 3 | Due: Thursday, Mar 19, 2026 | Modules 1-2 | ⏳ Pending |  |
| 4 | Due: Thursday, Apr 12, 2026 | Modules 1-3 | ⏳ Pending |  |
| 5 | Due: Thursday, Apr 16, 2026 | Modules 1-4 | ⏳ Pending |  |
| 6 | Due: Monday, Apr 20, 2026 | Modules 1-5 | ⏳ Pending |  |
