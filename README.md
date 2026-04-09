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
| 4 | Advanced Search (Hill Climbing, Simulated Annealing), Game Theory (Minimax, Nash Equilibrium) | Module 3 `diagnosis.json`, maintenance actions + budget (JSON) | `maintenance_plan.json` (assignments, tradeoffs, minimax contingency, 2×2 Nash scan) | Modules 1-3 | Checkpoint 4 (Week 9) |
| 5 | Supervised Learning (Logistic Regression, Evaluation Metrics, Neural Networks) | Labeled dataset, Feature engineering pipeline, Training parameters | Trained model with metrics, Confusion matrix, Real-time predictions, Performance comparison | Modules 1-4 | Checkpoint 5 (Week 11) |
| 6 | Reinforcement Learning (MDP, Q-Learning, Policy Functions) | Module 3 `diagnosis.json`, JSON MDP (`mdp.json`), training config | `rl_policy.json`, `rl_training.json`, `rl_metrics.json` | Modules 1–4 (Module 5 optional extension) | Checkpoint 6 (Week 13) |

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
  "heuristic": "time_to_failure",
  "a_star_weight": 1.0,
  "max_total_paths": 20000,
  "max_paths_per_start": 80
}
```

- `heuristic`: `"time_to_failure"` or `"sensor_distance"`.
- `max_total_paths` / `max_paths_per_start`: optional caps on path enumeration; set to `null` for no limit (can be very slow on large, dense graphs).

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
- **Graph building approach**: Since the dataset has one record per machine (not time-series), the graph connects states that differ by exactly one sensor bin (full pairwise similarity edges, bidirectional). **All** CSV rows are used—there is no record sampling in the runner.
- Graph states are defined by discretized sensor combinations (binning approach)
- Search algorithms explore paths leading to failure states using BFS/DFS from states adjacent to failures (or from all non-failure states if needed). Identical paths found by BFS, DFS, and A* are deduplicated before pattern extraction.
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

## Module 3: Equipment Diagnosis (First-Order Style KB)

- **Topic:** First-order logic themes—predicates, variables, **unification**, and **forward chaining** (Horn-style rules in JSON).
- **Goal:** In **batch** per `equipment_id`, combine Module 1 classifications and **required** Module 2 outputs with an editable knowledge base to produce ranked hypotheses, heuristic confidence scores, explanation chains, and inspection text.

### Inputs

1. **Knowledge base JSON** (e.g. `src/data/module3/kb.json`)
   - Top-level key `"rules"`: array of objects with:
     - `id` (string), `priority` (int, higher fires first for provenance),
     - `antecedents`: list of atoms (each atom is a JSON array: predicate string, then constants or variables),
     - `consequent`: single atom array,
     - `inspection` (optional string, shown when that rule derives a diagnosis).
   - **Variables** are strings whose first character is `?` (e.g. `?e` for equipment). All other strings in atoms are constants.

```json
{
  "rules": [
    {
      "id": "example_rule",
      "priority": 70,
      "antecedents": [
        ["violated", "?e", "vibration_high"],
        ["m2_on_failure_path", "?e"]
      ],
      "consequent": ["suggests", "?e", "rotating_component_stress"],
      "inspection": "Inspect bearings and alignment."
    }
  ]
}
```

2. **Module 1** `classifications.jsonl` (one JSON object per line), same shape as Module 1 output.

3. **Module 2** (both required):
   - `sequences.json` — object with `"sequences"` array (from `run_module2`).
   - `warning_signs.json` — object with `"warning_signs"` array.

The engine derives ground facts per equipment (e.g. `status`, `violated`, `m1_max_confidence`, `m2_on_failure_path`, `m2_top_predictive`) from these files; rule authors should align predicate names with Module 1 `violated_rules` strings and the built-in fact predicates.

### Outputs

- **`diagnosis.json`** — object with key `"equipment"`: array of blocks, one per `equipment_id` found in classifications. Each block includes:
  - `equipment_id`, `diagnoses` (ranked list with `hypothesis`, `score`, `supporting_rule_ids`, `explanation`, `inspection`),
  - `primitive_facts` (ground atoms fed to the engine),
  - `meta` (summary fields for M1/M2 context).

### Assumptions

- `equipment_id` values are consistent between Module 1 rows and Module 2 `machines` lists so historical pattern facts line up.
- Module 3 does not re-run Module 1 or 2; it reads their artifacts only.

### Public Interfaces

Under `src/equipment_monitoring/module3/`:

- `infer_batch(kb_path, classifications_path, sequences_path, warning_signs_path) -> dict`
  - Returns a JSON-serializable dict with `"equipment"` array.
- `run_module3(kb_path, classifications_path, sequences_path, warning_signs_path, output_dir) -> None`
  - Writes `output_dir / "diagnosis.json"`.

---

## Module 4: Maintenance Schedule Optimizer

- **Topic:** **Hill climbing**, **simulated annealing** over discrete maintenance assignments; small **minimax** (one full repair vs worst-case failure target) and **pure Nash** enumeration on a 2×2 operator–environment game built from schedule costs.
- **Goal:** Turn Module 3 risk signals into a feasible per-equipment action plan under budget and downtime caps, report tradeoffs across budget scales, and attach a short game-theoretic contingency summary for demos and reports.

### Inputs

1. **Module 3** `diagnosis.json` (same shape as Module 3 output). Per-equipment **risk** is derived as the max diagnosis `score`, or from `meta` (`m1_max_confidence` / `m2_top_predictive`) when there are no `suggests`-style diagnoses.
2. **Module 4 config JSON** (e.g. `src/data/module4/module4_config.json`):
   - `actions`: list of `{ "id", "cost", "downtime_hours", "risk_multiplier" }` (multiplier scales residual failure penalty for that equipment).
   - `budget`, `max_total_downtime_hours`, `failure_cost_scale` (weights failure-risk term in the objective).
   - Optional `hill_climbing` / `simulated_annealing` blocks for iteration limits.
3. **Optional production schedule JSON** (e.g. `src/data/module4/production_schedule.json`): `label`, `notes`, and optional `max_total_downtime_hours`. When set, the optimizer uses `min(base max_total_downtime_hours, schedule value)` so peak production can tighten the aggregate downtime cap without editing the main config.

### Outputs

- **`maintenance_plan.json`** — includes `assignments`, `totals` (maintenance vs failure penalty), `meta` (production-schedule merge details and effective downtime cap), `optimization` (hill climbing vs simulated annealing objectives), `tradeoffs` (objective vs scaled budget), `contingency` (single-repair minimax), and `game_analysis` (2×2 payoffs, **pure** Nash equilibria, and a **mixed-strategy** Nash for the operator payoff matrix under a **zero-sum** proxy). See `game_analysis.mixed_nash_zero_sum_row_matrix.equilibrium` for probabilities and game value.

### Public interfaces

Under `src/equipment_monitoring/module4/`:

- `optimize_maintenance_plan(diagnosis_path, config_path, *, production_schedule_path=None) -> dict`
- `run_module4(diagnosis_path, config_path, output_dir, *, production_schedule_path=None) -> None` — writes `maintenance_plan.json`.

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
├── CONTRIBUTING.md           # team workflow (commits, PRs, tests)
└── README.md                 # this file
```

Module 1 code lives in `src/equipment_monitoring/module1/` with matching tests in `unit_tests/module1/`.
Module 2 code lives in `src/equipment_monitoring/module2/` with matching tests in `unit_tests/module2/`.
Module 3 code lives in `src/equipment_monitoring/module3/` with matching tests in `unit_tests/module3/` and `integration_tests/module3/`.
Module 4 code lives in `src/equipment_monitoring/module4/` with tests in `unit_tests/module4/` and `integration_tests/module4/`.
Module 6 code lives in `src/equipment_monitoring/module6/` with tests in `unit_tests/module6/` and `integration_tests/module6/`.

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

**Module 1 → Module 2 pipeline (shared data):** Module 2 depends on Module 1. You can run both on the same dataset when the CSV uses Module 1’s schema plus a `failure_status` column:

1. Use a CSV with columns: `timestamp`, `equipment_id`, `temperature`, `vibration`, `pressure`, `failure_status`.
2. Run Module 1 (produces `classifications.jsonl` and `alerts.txt`).
3. Run Module 2 with `--data-format module1` and optionally `--classifications` pointing to Module 1’s `classifications.jsonl`. Warning signs will include `module1_anomaly_rate` when classifications are provided.

Example (from project root, with `PYTHONPATH=src`):

```bash
# Step 1: Run Module 1 on shared CSV
python -m equipment_monitoring.cli --module 1 \
  --config data/module1/config.json \
  --specs data/module1/equipment_specs.json \
  --readings data/readings_with_failures.csv \
  --output-dir outputs/module1

# Step 2: Run Module 2 on same CSV, using Module 1 classifications
python -m equipment_monitoring.cli --module 2 \
  --data data/readings_with_failures.csv \
  --graph-config src/data/module2/graph_config.json \
  --search-params src/data/module2/search_params.json \
  --output-dir outputs/module2 \
  --data-format module1 \
  --classifications outputs/module1/classifications.jsonl
```

- `--data-format`: `timestamped` (default) or `module1`. Use `module1` when the CSV has Module 1 column names and optional `failure_status`.
- `--classifications`: Optional path to Module 1’s `classifications.jsonl`; enriches warning signs with `module1_anomaly_rate`.

### Module 3

Run Module 3 **after** Module 1 and Module 2 on the same logical dataset (Module 1 schema CSV recommended so M1 + M2 + M3 share one file).

```bash
python -m equipment_monitoring.cli --module 3 \
  --kb src/data/module3/kb.json \
  --classifications outputs/module1/classifications.jsonl \
  --sequences outputs/module2/sequences.json \
  --warning-signs outputs/module2/warning_signs.json \
  --output-dir outputs/module3
```

Expected output:

- `outputs/module3/diagnosis.json` — diagnoses, explanations, and inspection strings per equipment.

**Full pipeline** (from project root, `PYTHONPATH=src`): run Module 1, then Module 2 with `--data-format module1` and `--classifications`, then Module 3 as above. Use the same readings CSV path for Module 1 and Module 2.

### Module 4

Run after Module 3 (reads `diagnosis.json` only):

```bash
python -m equipment_monitoring.cli --module 4 \
  --diagnosis outputs/module3/diagnosis.json \
  --module4-config src/data/module4/module4_config.json \
  --production-schedule src/data/module4/production_schedule.json \
  --output-dir outputs/module4
```

If `--module4-config` is omitted, the CLI defaults to `src/data/module4/module4_config.json` relative to the `equipment_monitoring` package (run from project root with `PYTHONPATH=src`). `--production-schedule` is optional.

Expected output:

- `outputs/module4/maintenance_plan.json`

### Module 6

- **Topic:** MDP from JSON, tabular Q-learning, ε-greedy exploration, greedy policy export, baselines (always-defer, random).
- **Goal:** Learn a policy over **risk buckets** (`risk_low`, `risk_mid`, `risk_high`) using the same action ids as Module 4 (`defer`, `inspect`, `repair`). Training samples transitions from **`mdp.json`**. **Module 5 is not required.**

**Inputs:** Module 3 `diagnosis.json` (risk = max diagnosis score or meta blend, same as Module 4), `src/data/module6/module6_config.json`, and `src/data/module6/mdp.json` (states, actions, stochastic transitions as `[p, next_state, reward]` lists summing to 1; optional `initial_state_weights` if diagnosis has no equipment rows).

**Outputs:**

| File | Top-level keys (summary) |
|------|---------------------------|
| `rl_policy.json` | `policy` (state → action), `q_table` (state → action → Q), `meta` (paths, hyperparameters, `module5_required`) |
| `rl_training.json` | `episodes` (list of `episode`, `return`, `steps`, `epsilon`, `return_mean_so_far`), `meta` (`mean_return_last_window`, `window_size`) |
| `rl_metrics.json` | `trained_policy_last_window`, `baseline_always_defer`, `baseline_random` (each: mean/std + episode counts), `mdp` (state/action lists) |

**Code:** `run_module6(diagnosis_path, module6_config_path, output_dir, *, mdp_path=None, module4_config_path=None, random_seed=None)`.

Run after Module 3 (Module 4 optional):

```bash
PYTHONPATH=src python3 -m equipment_monitoring.cli --module 6 \
  --diagnosis outputs/module3/diagnosis.json \
  --output-dir outputs/module6
```

Defaults: `--module6-config` → `src/data/module6/module6_config.json`. Use `--mdp` to override the MDP path. Use `--module4-config` to override action validation (otherwise uses `module4_config_path` from the Module 6 config when set).

### Static HTML Report (`--report`)

Any module run can also generate/update a static report by adding `--report`.
By default, the report is written to `report.html` under the inferred outputs root.
If `--output-dir` is `outputs/moduleN`, the inferred root is `outputs/`.

```bash
python -m equipment_monitoring.cli --module 3 \
  --kb src/data/module3/kb.json \
  --classifications outputs/module1/classifications.jsonl \
  --sequences outputs/module2/sequences.json \
  --warning-signs outputs/module2/warning_signs.json \
  --output-dir outputs/module3 \
  --report
```

To write to a custom location, pass `--report-path`:

```bash
python -m equipment_monitoring.cli --module 4 \
  --diagnosis outputs/module3/diagnosis.json \
  --module4-config src/data/module4/module4_config.json \
  --output-dir outputs/module4 \
  --report \
  --report-path outputs/my_report.html
```

Report content includes:
- Module 1 summary/anomaly tables (when `classifications.jsonl` exists)
- Module 2 top sequences and warning signs
- Module 3 diagnosis cards and inspection recommendations
- Optional Module 4 plan summary when `maintenance_plan.json` exists
- Optional Module 6 RL policy summary when `module6/rl_policy.json` exists

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
- `unit_tests/module2/test_module2_config.py` - Graph and search JSON config loading

**Module 3:**
- `unit_tests/module3/test_logic.py` - Unification, substitution, matching, forward chaining
- `unit_tests/module3/test_kb_loader.py` - KB JSON loading and validation errors
- `unit_tests/module3/test_facts.py` - Ground facts from Module 1/2 artifacts
- `unit_tests/module3/test_diagnosis.py` - Diagnosis scoring, explanations, `build_diagnosis_record`
- `unit_tests/module3/test_runner.py` - `infer_batch` and `run_module3` output shape

**Module 6:**
- `unit_tests/module6/test_mdp_loader.py` - MDP / config validation
- `unit_tests/module6/test_q_learning.py` - ε schedule, Q-update, short training run
- `unit_tests/module6/test_state.py` - risk buckets from `diagnosis.json`; invalid/missing diagnosis → `Module6ConfigError`
- `unit_tests/module6/test_module6_runner.py` - output files and policy shape

**Module 4:**
- `unit_tests/module4/test_loader.py` - config and diagnosis parsing
- `unit_tests/module4/test_objective.py` - feasibility and objective
- `unit_tests/module4/test_optimize.py` - hill climbing
- `unit_tests/module4/test_game_theory.py` - minimax and Nash helpers
- `unit_tests/module4/test_module4_runner.py` - `optimize_maintenance_plan` / `run_module4`
- `unit_tests/module4/test_production_schedule.py` - production JSON and downtime cap merge
- Invalid JSON for Module 4 / diagnosis / production loaders raises `Module4ConfigError` (see `test_loader.py`).

### Integration Tests (`integration_tests/`)

**Module 1:**
- `integration_tests/module1/test_module1_smoke.py` - Full pipeline smoke test

**Module 2:**
- `integration_tests/module2/test_module2_smoke.py` - Full pipeline smoke test on timestamped dataset
- `integration_tests/module2/test_module1_module2_integration.py` - Module 1 then Module 2 on same dataset; verifies Module 2 can use Module 1 schema CSV and classifications

**Module 3:**
- `integration_tests/module3/test_module3_smoke.py` - Module 1 → Module 2 → Module 3 end-to-end on shared CSV

**Module 4:**
- `integration_tests/module4/test_module4_smoke.py` - Module 1 → Module 4 on shared CSV; optional production cap (zero downtime → all defer)

**Module 6:**
- `integration_tests/module6/test_module6_smoke.py` - Module 6 on `outputs/full_pipeline/module3/diagnosis.json` when present

### Running Tests

Run all tests:
```bash
pytest unit_tests/ integration_tests/ -v
```

Run Module 2 tests only:
```bash
pytest unit_tests/module2/ integration_tests/module2/ -v
```

Run Module 3 tests only:
```bash
pytest unit_tests/module3/ integration_tests/module3/ -v
```

---

## Checkpoint Log

Progress tracking against course checkpoints:

| Checkpoint | Date | Modules Included | Status | Evidence |
| ---------- | ---- | ---------------- | ------ | -------- |
| 1 | Completed: Wednesday, Feb 11, 2026 | Module 1 | ✅ Complete | Module 1 fully implemented with unit and integration tests. CLI working, outputs generated. |
| 2 | Due: Thursday, Feb 26, 2026 | Module 2 | ✅ Complete | Module 2 fully implemented: graph building, BFS/DFS/A* search, pattern extraction, warning sign ranking. All tests passing. |
| 3 | Due: Thursday, Mar 19, 2026 | Modules 1-2 | ⏳ Pending | Confirm with instructor when submitted. |
| 4 | Due: Thursday, Apr 12, 2026 | Modules 1-3 | ⏳ In progress | Module 3 implemented; `README.md` documents I/O and CLI; `checkpoint_3_*` reports; see `integration_tests/module3/`. |
| 5 | Due: Thursday, Apr 16, 2026 | Modules 1-4 | ⏳ Pending |  |
| 6 | Due: Monday, Apr 20, 2026 | Modules 1-5 | ⏳ Pending |  |
