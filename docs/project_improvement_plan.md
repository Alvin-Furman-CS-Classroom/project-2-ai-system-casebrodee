# Project improvement plan

This document is the **authoritative roadmap** for incremental hardening of the industrial monitoring system (modules 1–4 and 6, reporting, tests, and tooling). Work proceeds **one phase at a time**; each phase should be reviewed and approved before the next begins.

---

## Module 5 (supervised learning)

**Status:** **Future work** — natural extensions include logistic regression, evaluation metrics, neural nets, and a labeled feature pipeline tied to Modules 1–4.

**Current position:** We **do not plan to implement Module 5** in this repository for the current course delivery. The system is complete through **Module 6 (tabular RL)** without Module 5. If the course or a fork later adds Module 5, this doc and the README module table should be updated.

---

## Phase 0 — Scope locked (this document)

**Deliverables**

- This file: full phased plan including **Phase 8 (fleet summary JSON)**.
- CONTRIBUTING notes on phased execution and approval.

**Done when**

- Stakeholders agree this plan is the source of truth.

---

## Phase 1 — RL narrative for readers and graders

**Goal:** Clarify that returns are cost-shaped, scale comes from `mdp.json`, and **trained vs. baselines** is the primary quality read.

**Tasks**

- README Module 6: short subsection on return scale and baseline comparison.
- Reporting: reinforce one sentence if needed (no contradiction with “higher / closer to zero is better”).
- Optional: extend `module6-plan.md` or a short FAQ with ε-greedy / episode definition.

**Done when**

- README and report wording align.

---

## Phase 2 — Module 6 methodology

**Goal:** Reproducibility notes, optional multi-seed story, **golden MDP test** on a tiny fixture with known optimal greedy action; document toy reward units.

**Tasks**

- Document `num_episodes`, `max_steps_per_episode`, `random_seed`, ε schedule; note policy variance across seeds.
- Add minimal MDP fixture + test that greedy policy matches expectation after training (fixed seed).
- State in docs that MDP rewards are **toy units**, not calibrated currency.

**Done when**

- New test guards Q-learning / policy export; docs updated.

**Completed (implementation snapshot)**

- Fixture: `src/data/module6/fixtures/golden_policy_mdp.json` (states `g_low` / `g_high`; optimal greedy `inspect` / `repair`).
- Test: `unit_tests/module6/test_golden_mdp.py` (γ=0, horizon 1, fixed seed).
- README: **Reproducibility and variance** + golden regression note; testing index updated.
- `module6-plan.md`: toy reward units under MDP JSON; FAQ entries for golden test and hyperparameters.

---

## Phase 3 — Pipeline ergonomics

**Goal:** One documented command (e.g. Makefile or script) for M1→M2→M3→M4→M6 and report regeneration.

**Tasks**

- Choose Makefile vs `scripts/run_pipeline.sh` (or similar).
- Targets: full pipeline + `report` (and document canonical data paths).

**Done when**

- README “full stack” points at one entrypoint; expected `outputs/` layout listed.

**Completed (implementation snapshot)**

- **`Makefile`** at repo root: `make pipeline` (M1→M6 + `make report`), `make report`, `make m1`…`m6` with dependency chain; defaults use `outputs/full_pipeline/data/` for Module 1 inputs; override variables documented in `make help`.
- **README** “Full pipeline (`make`)” table of targets and expected `outputs/` tree.

---

## Phase 4 — Reporting UX

**Goal:** Module 6 state gloss (`_m1hot` explained inline); cleaner loading/error panel.

**Tasks**

- Human-readable gloss per policy row (thresholds from `meta.m1_alert` when present).
- Group or prioritize optional vs required missing files in the report.

**Done when**

- Report is self-explanatory for `_m1hot` without reading `state.py`.

**Completed (implementation snapshot)**

- **`reporting._module6_state_gloss`**: per-row plain-language line for each policy state; rich mode uses `meta.m1_alert` thresholds when present.
- **Module 6 HTML table**: third column **“What this state means”**.
- **Data loading panel**: split into **Modules 1–3 (core)** vs **Modules 4 & 6 (optional)** with explanatory subtitle.

---

## Phase 5 — Tests and CI

**Goal:** Integration test on **tiny fixtures** (no dependency on `outputs/full_pipeline`); full chain always runs in CI.

**Tasks**

- Fixtures + temp fast Module 6 config; assert outputs + report generation.
- Keep optional smoke on real `full_pipeline` if present.

**Done when**

- `pytest` covers the chain every run.

**Completed (implementation snapshot)**

- **`integration_tests/pipeline/test_full_stack_fixtures.py`**: tmp CSV + Module 1–3–4–6 using repo `src/data` configs; fast Module 6 (`num_episodes` 80); `generate_report`; asserts RL outputs, `#module6` and gloss in HTML, empty `errors_core` on reload.
- Existing optional **`outputs/full_pipeline`** smoke in `integration_tests/module6/test_module6_smoke.py` unchanged.

---

## Phase 6 — Incremental typing

**Goal:** `mypy` on scoped paths (`module6`, `reporting`) with pragmatic strictness.

**Tasks**

- `pyproject.toml` mypy config; type public surfaces; fix straightforward issues.

**Done when**

- Documented `mypy` command passes on agreed paths.

**Completed (implementation snapshot)**

- **`pyproject.toml`** — `[tool.mypy]` with `files =` Module 6 package + `reporting.py`, `explicit_package_bases`, `mypy_path = "src"`, and pragmatic strict flags (`disallow_untyped_defs`, etc.).
- **`requirements.txt`** — `mypy>=1.8.0`.
- **`Makefile`** — **`make typecheck`** → `$(PYTHON) -m mypy`.
- **README** — Static typing subsection; **`make typecheck`** in the targets table.
- **CONTRIBUTING** — reminder to run typecheck when touching those paths.

---

## Phase 7 — Documentation alignment

**Goal:** README, `module6-plan.md`, checkpoint/agents text match behavior; Module 5 described as **future work, not scheduled**; pipeline + RL narrative linked.

**Tasks**

- README Module 6: six-state MDP, `--classifications`, `meta.m1_max_confidence`, three RL outputs, link to pipeline + this plan.
- `module6-plan.md` / CONTRIBUTING / AGENTS as needed.
- Module table footnote or Module 5 row note: future work, not currently planned.

**Done when**

- No doc implies Module 5 is implemented or imminent.

**Completed (implementation snapshot)**

- **README** — Module plan table: row 5 marked †, footnote on Module 5 not in repo; row 6 inputs include classifications / `m1_max_confidence`; “Depends on” for Module 6 is Modules 1–4 only; **`make pipeline`** pointer + anchor link from Module 6 section.
- **AGENTS.md** — Table aligned with implemented I/O; Module 5 †; links to improvement plan and `make pipeline`.
- **module6-plan.md** — Design table rows for state space and training scope match shipped behavior.
- **checkpoint_6_module_explanation.md** — Checklist wording for Module 5 future work.

---

## Phase 8 — Fleet summary JSON

**Goal:** One deterministic JSON artifact summarizing fleet health from **existing** outputs (counts, optional M4 totals, Module 6 policy snippet + key metrics).

**Tasks**

- Schema sketch: e.g. `generated_at`, `outputs_root`, module summaries, `module6` block from `rl_policy.json` / `rl_metrics.json` when present.
- Implement: function + CLI flag or `make summary`, or hook next to `--report`.
- README paragraph.

**Done when**

- Regenerating from current `outputs/` is reproducible and tested at least minimally.

**Completed (implementation snapshot)**

- **`reporting.build_fleet_summary`** / **`write_fleet_summary`** — UTC `generated_at`, artifact flags, `load_errors`, summaries for modules 1–4 and **module6** (metrics, full **`policy`** dict, optional hyperparameters from training meta).
- **`Makefile`** — **`make summary`** writes **`$(OUT)/fleet_summary.json`**; documented in **`make help`**.
- **CLI** — **`--fleet-summary`** after a successful module run writes **`fleet_summary.json`** next to the inferred outputs root.
- **Tests** — **`unit_tests/reporting/test_reporting.py`** (build + custom write path); **`integration_tests/pipeline/test_full_stack_fixtures.py`** asserts summary file and schema after full stack.
- **README** — targets table, expected `outputs/` layout, **`--fleet-summary`**, and **`make summary`**.

---

## Execution order

| Step | Phase   | Notes                                      |
| ---- | ------- | ------------------------------------------ |
| 1    | Phase 0 | This doc (+ CONTRIBUTING pointer)          |
| 2    | Phase 1 | README + report copy                       |
| 3    | Phase 2 | Golden MDP + methodology docs              |
| 4    | Phase 3 | Makefile / script                          |
| 5    | Phase 5 | Fixture integration (can align with Phase 3 paths) |
| 6    | Phase 4 | Reporting gloss + errors                   |
| 7    | Phase 6 | mypy                                       |
| 8    | Phase 7 | Full doc pass + Module 5 future-work       |
| 9    | Phase 8 | Fleet summary JSON                         |

Phases 5 and 3 may overlap slightly once paths are fixed; Phase 7 README edits can merge with Phase 1 where it reduces churn.

---

## Approval gate

After each phase: confirm **done when** criteria, then explicitly approve the **next** phase before implementation continues.
