# Module 2 Plan: Failure Pattern Discovery



## Module 2 Context

- **Goal:** Discover sequences of sensor changes that precede failures using **Uninformed Search (BFS, DFS)** and **Informed Search (A*, Heuristics)**. Produce failure sequences, optional visualizations, and a ranked list of warning signs.
- **Inputs (from PROPOSAL.md):**
  - Historical sensor data with known failure events (timestamps or ordering + failure labels).
  - Graph structure representing equipment states and transitions.
  - Search parameters (e.g., how far back to look, minimum pattern length, max depth).
- **Outputs:**
  - Discovered sequences that precede failures (with frequency/timing stats).
  - Optional visualizations of degradation over time.
  - Ranked warning signs (e.g., “vibration rising over 3 steps” predicts failure with frequency X).
- **Depends on:** Module 1 (we can optionally use Module 1’s classifier to label anomalies; at minimum we need temporal + failure-labeled data).

---

## Real Datasets (Prioritize Timestamped)

We will use real data under `src/data/`, starting with datasets that have timestamps or clear temporal ordering:

| Dataset | Timestamp / ordering | Failure / label | Use in Module 2 |
|--------|----------------------|------------------|------------------|
| **machine_failure_data_timestamp.csv** | `Timestamp` (datetime) | `Failure_Status` (0/1) | **Primary:** per-machine time series; build sequences leading to `Failure_Status=1`. |
| **MAINTENANCE PREDICTIVE FOR INDUSTRIAL MACHINES.csv** | `Runtime` (cumulative) | `Failures`, `Remaining_Useful_Life` | **Secondary:** order by Runtime per machine; sequences before failure. |
| **machine failure.csv** / **ai4i2020.csv** | Row order (UDI) or Product ID runs | `Machine failure`, TWF/HDF/PWF/OSF/RNF | **Optional:** treat row order as time; multiple failure types for richer patterns. |

**Decision:** Implement and test first on **machine_failure_data_timestamp.csv** (explicit timestamps + failure labels). Add adapters later for Runtime-based or row-order datasets so the same search pipeline can consume them.

---

## Repository Structure for Module 2

- **Code:** `src/equipment_monitoring/module2/`
  - `io.py` — load historical CSV(s), normalize to a common “time-ordered readings + failure” structure (timestamp or sequence id, machine_id, sensor cols, failure_label).
  - `graph.py` — build graph: **states** (e.g., discretized sensor buckets or “normal”/“anomaly” from Module 1), **transitions** (time-ordered edges from one state to the next per machine).
  - `search.py` — BFS, DFS, and A* over the graph (e.g., from “normal” or any state backward/forward to failure states; or from failure backward to find preceding sequences).
  - `patterns.py` — wrap search results into “discovered sequences” and “warning signs” with frequency/ranking.
  - `config.py` — search parameters (max depth, lookback window, binning rules for discretization), paths to data.
  - Optional: `visualize.py` or integration with a simple plotting library for degradation-over-time plots (can be minimal for Checkpoint 2).
- **CLI:** Extend `src/equipment_monitoring/cli.py` with a Module 2 entrypoint (e.g. `--module 2` or `run_module2(data_path, config_path, output_dir)`).
- **Tests:** `unit_tests/module2/` (test_io, test_graph, test_search, test_patterns) and `integration_tests/module2/test_module2_smoke.py` (run pipeline on a small slice of the timestamped dataset and assert outputs).

---

## Graph Model (How We Build It)

- **States:** Discretize sensor readings so each row (or time window) maps to a state ID. Options:
  - **Option A:** Use Module 1’s classifier: run it on each row (with a small config) and define state = (equipment_id, status, e.g. “normal” vs “anomaly”). Simple, reuses Module 1.
  - **Option B:** Bin numeric columns (e.g., temperature low/medium/high) and state = (machine_id, temp_bin, vibration_bin, pressure_bin). No Module 1 dependency for the graph itself.
  - **Recommendation:** Start with Option B for clarity and to avoid coupling; optionally add Option A later so “anomaly” is one of the states.
- **Transitions:** For each machine, order rows by timestamp (or Runtime/row order). Add an edge from state at time t to state at time t+1. Optionally tag edges with “leads to failure” if the next row has failure=1.
- **Goal states:** Any state where the corresponding reading has failure=1 (or the next reading has failure=1, depending on how we define “preceding sequence”).

Search will then:
- **BFS/DFS:** Enumerate paths that lead to failure (e.g., from all states that eventually reach a failure state, or from failure backward to preceding states). Used to collect candidate sequences.
- **A*:** Use a heuristic (e.g., time-to-failure, or distance in sensor space to a known failure region) to rank or prioritize which sequences are most “predictive” or costly. Produces the ranked warning signs.

---

## Data Flow (End-to-End)

1. **Load:** Read timestamped CSV (and optionally others via adapter) into a list of records with a canonical time column and failure label.
2. **Graph build:** Discretize → states; for each machine, add transitions in time order; mark failure states.
3. **Search:** Run BFS/DFS to discover paths to failure; run A* to rank them (e.g., by heuristic cost or frequency).
4. **Patterns:** Aggregate paths into “sequences that precede failure” and “warning signs” (e.g., “state_sequence [A,B,C] → failure” with count and maybe timing stats).
5. **Output:** Write JSON (and optionally text) of discovered sequences and ranked warning signs; optional plots (e.g., one plot per machine showing state over time and failure point).

---

## Preparation Steps Before Coding

1. **Document Module 2 spec in README.md**  
   Add a “Module 2: Failure Pattern Discovery” section: inputs (historical CSV with timestamps + failure column, graph config, search params), outputs (sequence list, warning signs, optional viz), and which dataset we use first (machine_failure_data_timestamp.csv).

2. **Define canonical “historical record” format**  
   So that `module2/io.py` can emit a single format regardless of whether the source is timestamp CSV, Runtime CSV, or row-order CSV. Include: machine_id, time_key (timestamp or numeric order), sensor fields, failure_label.

3. **Define graph config and search params (JSON or code)**  
   E.g. bin boundaries for discretization, max_depth for BFS/DFS, lookback window (e.g., “only consider 50 steps before failure”), and A* heuristic choice (e.g., “time to failure” or “sensor distance to failure centroid”).

4. **Create skeletons**  
   Add `src/equipment_monitoring/module2/` with the files above (io, graph, search, patterns, config) and `unit_tests/module2/`, `integration_tests/module2/` with placeholder tests.

5. **Implement and test on timestamped data first**  
   Get the pipeline working on `machine_failure_data_timestamp.csv`; then add adapters for the other datasets if time permits.

---

## Testing Plan

- **unit_tests/module2/test_io.py:** Load timestamped CSV; check canonical record format; handle missing timestamp or failure column.
- **unit_tests/module2/test_graph.py:** Build graph from a tiny synthetic sequence; assert state count and edges (e.g., 3 states, 2 edges for A→B→C).
- **unit_tests/module2/test_search.py:** BFS/DFS on a small graph to a goal state; A* with a simple heuristic; assert path or sequence returned.
- **unit_tests/module2/test_patterns.py:** From a small set of paths, produce “sequences” and “warning signs” list; assert structure and ordering.
- **integration_tests/module2/test_module2_smoke.py:** Run full pipeline on a small slice of machine_failure_data_timestamp.csv (e.g., one machine or first N rows); assert output files exist and contain at least one sequence or warning sign when failures are present.
