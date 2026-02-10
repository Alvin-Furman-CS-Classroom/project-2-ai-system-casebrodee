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

Module 1 code will live in `src/equipment_monitoring/module1/` with matching tests in `unit_tests/module1/`.

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

## Running Module 1

Once Module 1 is implemented, you will be able to run it via a small CLI:

```bash
python -m equipment_monitoring.cli \
  --config data/module1/config.json \
  --specs data/module1/equipment_specs.json \
  --readings data/module1/readings.csv \
  --output-dir outputs/module1
```

Expected outputs:

- `outputs/module1/classifications.jsonl` — one JSON record per line.
- `outputs/module1/alerts.txt` — human-readable alerts.

The exact CLI options will be defined in `src/equipment_monitoring/cli.py`.

---

## Testing

### Unit Tests (`unit_tests/`)

Unit tests will mirror the structure of `src/`. For Module 1:

- `unit_tests/module1/test_config.py`
  - Loading configuration and equipment-spec JSON.
  - Handling missing or malformed fields.
  - Correctly applying equipment-specific overrides.
  - Edge cases around threshold boundaries (exactly at `min`/`max`).

- `unit_tests/module1/test_rules.py`
  - Correct detection of:
    - `*_high` and `*_low` conditions at and beyond thresholds.
    - Multiple simultaneous violations for one reading.
    - No violations when readings are within range.
  - Handling of missing values (e.g., `missing_temperature` rules).

- `unit_tests/module1/test_classifier.py`
  - End-to-end classification of synthetic readings using simple configs/specs.
  - Asserting status, violated rules, and confidence values.
  - Scenarios with:
    - all-normal readings,
    - clearly anomalous readings,
    - mixed batches (normal + anomaly).

- `unit_tests/module1/test_io.py`
  - Reading well-formed CSVs into internal data structures.
  - Writing JSONL classifications and alert text files.
  - Basic round-trip behavior for a tiny synthetic CSV.

### Integration Tests (`integration_tests/`)

For Module 1, a basic smoke test will live in `integration_tests/module1/`:

- Run the full Module 1 pipeline on a tiny synthetic dataset.
- Assert that:
  - Output files exist.
  - The expected number of anomalies is detected.
  - Specific `violated_rules` tags appear in the outputs.

---

## Checkpoint Log

Use this section to track progress against course checkpoints:

| Checkpoint | Date | Modules Included | Status | Evidence |
| ---------- | ---- | ---------------- | ------ | -------- |
| 1 |  | Module 1 |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |
| 6 |  |  |  |  |

