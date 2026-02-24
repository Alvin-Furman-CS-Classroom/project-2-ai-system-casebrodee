# Module 2: Review and Suggested Improvements

Your partner has the core pipeline in place: IO, graph building, BFS search, pattern extraction, ranking, Module 1 integration, CLI, and tests. Below is what’s already there and what could be added or improved so the module fully matches the spec and rubric.

---

## What’s Already in Place

| Component | Status |
|----------|--------|
| **IO** | `load_timestamped_csv`, `load_module1_schema_csv`, `load_classifications_jsonl`, `HistoricalRecord` |
| **Graph** | `State`, `Graph`, `build_graph` (temporal + similarity edges), `state_to_records` |
| **Config** | `GraphConfig`, `SearchParams` with JSON loading, discretization, heuristic choice |
| **Search** | BFS, DFS, and A* implemented in `search.py` with two heuristics |
| **Patterns** | `FailureSequence`, `WarningSign`, `extract_sequences`, `rank_warning_signs` (with Module 1 anomaly rate) |
| **Runner** | Full pipeline, sampling, `data_format`, `classifications_path` |
| **CLI** | `--module 2` with required args and optional `--classifications` |
| **Tests** | Unit tests for io, graph, config, search, patterns; smoke + Module 1–Module 2 integration |

---

## Gaps and Improvements (by priority)

### 1. **DFS is not used in the pipeline** (Topic engagement)

- **Spec:** “Uninformed Search (BFS, DFS)” for path enumeration.
- **Current:** `discover_failure_sequences` only calls BFS.
- **Change:** Use both BFS and DFS (e.g. run BFS from half the start states and DFS from the rest, or add a `search_strategy: "bfs" | "dfs" | "both"` in `SearchParams` and branch in `discover_failure_sequences`). That way both uninformed searches are clearly exercised in the main flow.

### 2. **A* is not used in the pipeline** (Topic engagement)

- **Spec:** “Informed Search (A*, Heuristics)” and “A* to rank or prioritize.”
- **Current:** A* and heuristics exist in `search.py` but are never called from `runner` or `discover_failure_sequences`. `SearchParams.heuristic` and `a_star_weight` are unused.
- **Change (pick one or both):**
  - **Option A:** In `discover_failure_sequences`, for some start states run A* (with `heuristic_time_to_failure` or `heuristic_sensor_distance` from config) and add the resulting path to the path list. That makes “informed search” part of discovery.
  - **Option B:** After BFS/DFS discovery, run A* from one representative start per sequence to get a “best path” and use it for ordering or as the canonical path for that pattern. That uses A* for ranking/prioritization.

### 3. **Visualization is still a stub** (Outputs)

- **Spec:** “Optional visualizations (degradation over time plots).”
- **Current:** `visualize.py` has only TODOs and `pass`.
- **Change:** Add a minimal implementation (e.g. matplotlib): one plot per machine with state index (or time) on x-axis and a simple state indicator (or sensor bin index) on y-axis, with failure points marked. Call it from `runner` only when an “enable visualization” flag or output dir is set, so it stays optional.

### 4. **TODOs in patterns.py** (Output quality)

- **`avg_time_to_failure`** is always `0.0` (comment: “TODO: Calculate from actual time differences”). To implement: use `graph.state_to_records` and the `time_key` on the last state of the sequence and the failure state to compute time deltas and average them per sequence.
- **`false_positive_rate`** is always `0.0` (comment: “TODO: Calculate false positive rate”). To implement: for each sequence, count how often that sequence appears in the graph without leading to a failure within a bounded depth; then `false_positive_rate = false_positives / (true_positives + false_positives)`.

Filling these in makes the “failure sequences with frequency and timing statistics” and “ranked warning signs” outputs stronger for the rubric.

### 5. **Heuristic strength** (Nice to have)

- **Current:** `heuristic_time_to_failure` returns a constant `1.0` for non-failure states, so A* behaves like uniform-cost search.
- **Change:** When `graph.state_to_records` is available, compute a simple “time to failure” from record timestamps (e.g. min time difference from this state’s records to any failure state’s records) and use that as the heuristic value so A* actually prefers states closer in time to failure.

### 6. **Wire SearchParams into search** (Consistency)

- **Current:** `search_params.heuristic` and `search_params.a_star_weight` are not passed into any search function.
- **Change:** When A* is invoked (from item 2), select the heuristic from `search_params.heuristic` (e.g. `"time_to_failure"` → `heuristic_time_to_failure`, `"sensor_distance"` → `heuristic_sensor_distance`) and pass `search_params.a_star_weight` as the `weight` argument to `a_star`.

---

## Suggested order of work

1. **Use DFS in the pipeline** (small change in `discover_failure_sequences`).
2. **Use A* in the pipeline** (e.g. Option A above) and wire `heuristic` and `a_star_weight` from `SearchParams`.
3. **Implement or re-implement `avg_time_to_failure` and `false_positive_rate`** in `patterns.py` (you reverted this earlier; you can reintroduce it with tests).
4. **Add minimal visualization** in `visualize.py` and call it from the runner when requested.
5. **Improve `heuristic_time_to_failure`** using `state_to_records` if you want A* to be more informative.

If you tell me which of these you want (e.g. “1 and 2 only” or “all except visualization”), I can outline or write the exact code changes next.
