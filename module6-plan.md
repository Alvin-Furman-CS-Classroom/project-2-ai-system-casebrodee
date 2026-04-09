# Module 6 Plan: Reinforcement Learning (MDP + Q-Learning + Policy)

## Context

- **Course topics:** MDP, Q-learning, policy (ε-greedy / greedy), performance metrics.
- **Goal:** Learn a **maintenance-style policy** over discrete states using **tabular Q-learning**, with dynamics and rewards defined in **fixed JSON** (explicit MDP) and training driven by **rolling simulated episodes** (sampled transitions from that spec).
- **Depends on:** Modules **1–4** for realistic state construction and aligned action ids. **Module 5 is skipped for now**; state features use M1–M4 artifacts only. When README is updated, describe dependency as “Modules 1–4 (required for full pipeline); Module 5 optional future extension.”

---

## Design decisions (locked)

| Decision | Choice |
|----------|--------|
| Transition / reward source | **JSON file** defines the MDP (sparse transitions + rewards). |
| Training | **Simulated episodes:** each step samples `s', r` from the JSON-backed model. |
| Action space | Reuse **Module 4** action ids from `module4_config.json` (`defer`, `inspect`, `repair`) so policies are comparable to `maintenance_plan.json`. |
| State space (v1) | **Discrete buckets** derived primarily from **Module 3** `diagnosis.json` per-equipment risk (e.g. low / medium / high). Optional v1.1: add one bit from aggregated Module 1 anomaly rate. |
| Scope | **Single-equipment MDP** first (one `equipment_id` or aggregate “plant” state), or **parallel per-equipment** MDPs sharing the same transition JSON but different initial risk buckets—pick one in Phase 1 and document it. **Recommendation:** **per-equipment** episodes: state = risk bucket for that equipment; same `P(s'\|s,a)` for all (pedagogical simplification). |

---

## JSON artifacts

### 1. `src/data/module6/module6_config.json` (hyperparameters + paths)

- `gamma` (discount), `alpha` (Q learning rate), `epsilon_start`, `epsilon_end`, `epsilon_decay_episodes` (or linear decay schedule).
- `num_episodes`, `max_steps_per_episode`, `random_seed`.
- `risk_thresholds`: e.g. `[0.33, 0.66]` to map scalar risk → `risk_low` / `risk_mid` / `risk_high` state labels.
- `module4_config_path` or inline flag to load actions (validate ids against transitions).
- `mdp_path`: path to MDP JSON (below), or embed a `toy_mdp` key for demos/tests.

### 2. `src/data/module6/mdp.json` (or name `module6_mdp.json`)

Defines finite S, A, and stochastic transitions.

**Suggested shape (example—not prescriptive on exact nesting):**

```json
{
  "states": ["risk_low", "risk_mid", "risk_high"],
  "actions": ["defer", "inspect", "repair"],
  "initial_state_weights": { "risk_low": 0.5, "risk_mid": 0.3, "risk_high": 0.2 },
  "transitions": {
    "risk_low": {
      "defer": [[0.7, "risk_low", -5.0], [0.3, "risk_mid", -5.0]],
      "inspect": [[0.8, "risk_low", -205.0], [0.2, "risk_mid", -205.0]],
      "repair": [[0.9, "risk_low", -905.0], [0.1, "risk_mid", -905.0]]
    }
  }
}
```

Each inner triple: `[probability, next_state, reward]`. Probabilities per `(s,a)` must sum to 1 (validate in loader).

- Rewards should reflect **cost + failure risk** in spirit of Module 4 (negative numbers for minimization). Keep magnitudes consistent enough that Q-values converge in reasonable episode counts.

**Terminal states (optional):** If you add an absorbing `failed` state, episodes can end on transition into it; otherwise use fixed `max_steps_per_episode` only.

---

## Code layout

```
src/equipment_monitoring/module6/
  __init__.py
  loader.py          # module6_config + mdp.json validation; custom Module6ConfigError
  state.py           # diagnosis.json → per-equipment state key (string)
  mdp.py             # MDP dataclass; sample_next_state(rng), step interface
  q_learning.py      # Q-table, update, epsilon_greedy, decay
  runner.py          # run_module6(...) → writes outputs
```

- **`run_module6`** signature (sketch):  
  `diagnosis_path`, `mdp_path`, `module6_config_path`, `output_dir`, optional `module4_config_path` for action validation, optional `random_seed` override.

---

## Outputs (written to `output_dir`, e.g. `outputs/module6/`)

| File | Contents |
|------|----------|
| `rl_policy.json` | Greedy `state → action_id`; optional full `q_table`; `meta` (paths, seed, hyperparameters, note that M5 skipped). |
| `rl_training.json` | Per-episode return (and optionally per-episode length); running mean; epsilon per episode. |
| `rl_metrics.json` | Mean/std episode return over last N episodes; baseline comparisons (e.g. always-`defer`, random policy) evaluated on same MDP with fixed seeds. |

---

## CLI (`src/equipment_monitoring/cli.py`)

- Add `--module 6` to choices.
- Required: `--diagnosis`, `--output-dir`, `--module6-config` (or default repo path under `src/data/module6/`).
- MDP path: from config file **or** `--mdp` override.
- Optional: `--module4-config` to align/validate actions.
- Optional: `--report` hook consistent with other modules.

---

## Tests

| Location | What |
|----------|------|
| `unit_tests/module6/test_mdp_loader.py` | Invalid probabilities, unknown state/action, JSON errors. |
| `unit_tests/module6/test_q_learning.py` | Toy 2–3 state MDP: after enough episodes with **fixed seed**, Q-values or greedy policy match expected (golden values computed once by hand or by a short reference script). |
| `unit_tests/module6/test_state.py` | Risk bucketing from minimal `diagnosis.json` fixtures. |
| `unit_tests/module6/test_module6_runner.py` | Runner writes all three JSON files; schema smoke. |
| `integration_tests/module6/test_module6_smoke.py` | Optional: chain from repo fixture diagnosis + bundled `mdp.json`; run `run_module6`. |

---

## Reporting (optional phase)

- Extend `reporting.load_module_outputs` to read `module6/rl_policy.json` + `rl_metrics.json` when present.
- Small HTML section: policy action distribution, mean episode return, one-line “MDP states / actions count.”

---

## Implementation phases (step through in order)

**Phase 1 — Spec and data**

1. Freeze v1 state definition (risk buckets + field from `diagnosis.json` used as scalar risk).
2. Author **`mdp.json`** with the 3-state × 3-action pedagogical model (numbers tuned so Q-learning converges in ~few thousand steps).
3. Author **`module6_config.json`** with hyperparameters and paths.

**Phase 2 — Core RL (no diagnosis yet)**

4. Implement `mdp.py` + `loader.py` for MDP JSON.
5. Implement `q_learning.py` (table keyed by `(state, action)` strings).
6. Unit tests: loader validation + toy MDP policy / Q checks with fixed seed.

**Phase 3 — Runner and integration**

7. Implement `state.py` + `runner.py` (load diagnosis, assign state per equipment, run training episodes—either one MDP training run using **population** of equipment initial states sampled from diagnosis, or loop per equipment; **document the chosen interpretation** in runner docstring).
8. Write `rl_policy.json`, `rl_training.json`, `rl_metrics.json`.
9. CLI wiring + `unit_tests/module6/test_runner.py` + `integration_tests/module6/test_module6_smoke.py`.

**Phase 4 — Docs and polish**

10. README: new “Module 6” section (inputs, outputs, CLI example, dependency note without M5).
11. Optional: reporting HTML slice.
12. Run full test suite; code-review skill pass before checkpoint submission.

---

## Open item to resolve at start of Phase 3

**Training narrative:** Either

- **A)** One global Q-table: each episode picks one equipment at random, initial state from that equipment’s risk bucket, simulates until horizon—experience from all equipment updates one table (states do not include `equipment_id`), or  
- **B)** Same, but states include `equipment_id` (larger table; only if few machines in demo).

**Recommendation:** **A** for v1 (states = `risk_low` / `risk_mid` / `risk_high` only).

---

## Success criteria

- `pytest` passes for new unit and integration tests.
- CLI command documented in README runs end-to-end on sample outputs.
- Artifacts clearly separate **MDP definition** (JSON), **training trace** (`rl_training.json`), and **deliverable policy** (`rl_policy.json`).
- README / plan state explicitly that Module 5 is not required for this path.
