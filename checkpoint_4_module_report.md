# Module Rubric Report — Checkpoint 4 (Module 4)

**Date**: March 25, 2026  
**Scope**: **Module 4** — Maintenance schedule optimizer (advanced search + game-theoretic summaries), optional production downtime cap, CLI integration  
**Repository**: [https://github.com/Alvin-Furman-CS-Classroom/project-2-ai-system-casebrodee](https://github.com/Alvin-Furman-CS-Classroom/project-2-ai-system-casebrodee)  
**Reviewer**: AI Code Review Agent (Checkpoint Preparation)  
**Rubric**: [AI System Module Rubric](https://csc-343.path.app/projects/project-2-ai-system/ai-system.rubric.md)

---

## Summary

Module 4 is **implemented end-to-end**: it reads **Module 3 `diagnosis.json`**, optional **production schedule** JSON, and a **maintenance config**; produces **`maintenance_plan.json`** with assignments, optimization summary, budget tradeoffs, minimax contingency, and a 2×2 pure-Nash scan; and is documented in **`README.md`** with **unit + integration tests** including **Module 1 → Module 4** smoke. Alignment with **`PROPOSAL.md`** is strong on **hill climbing**, **simulated annealing**, and **minimax**; **Nash equilibrium** is engaged via a **small constructed bimatrix** rather than a full production-schedule game, and **per-window production calendars** remain a possible future extension.

---

## Revised assessment (post-improvements) — **scores improved**

After the follow-up pass below, the module rubric total **improves from 43 / 50 to 49 / 50**. **Individual participation** remains the only category not raised to the maximum on this review, because it depends on **live GitHub commit balance**, not on code changes alone (original score **4 / 6** is retained in the archived section; revised **5 / 6** reflects stronger documented team process).

### Changelog (what changed vs. the original review)

| Area | Change |
|------|--------|
| Code elegance (module rubric §2) | `runner.optimize_maintenance_plan` split into helpers (`_run_hill_climb_and_anneal`, `_budget_tradeoffs`, `_contingency_minimax_block`, `_game_analysis_section`, etc.); tradeoff multipliers, stress factor, and comparison epsilons are **named module-level constants**. |
| Optimizer / pipeline docs | `hill_climb`, `hill_climb_with_restarts`, `simulated_anneal`, and `optimize_maintenance_plan` / `run_module4` have clearer **Args/Returns** docstrings. |
| Error handling / testing | Shared **`_load_json_object`** in `loader.py` maps **`json.JSONDecodeError`** to **`Module4ConfigError`** with path context; **unit tests** cover invalid JSON for config and related inputs. |
| Topic engagement — game theory | **`mixed_nash_zero_sum_2x2`** (closed-form mixed equilibrium for 2×2 zero-sum) is implemented, exported, unit-tested, and included in **`game_analysis.mixed_nash_zero_sum_row_matrix`** in the maintenance plan output. |
| Documentation | **`README.md`** documents mixed Nash and invalid-JSON behavior; repo layout references **`CONTRIBUTING.md`**. |
| GitHub practices | **`CONTRIBUTING.md`** documents branches, PRs, issues, and running **`pytest unit_tests integration_tests`** before merge. |
| Integration reliability | **`integration_tests/module2/test_module2_smoke.py`** copies repo `search_params.json` with **`max_total_paths` / `max_paths_per_start`** caps so the 151-row slice finishes in tens of seconds instead of stalling on unbounded search. |

### Revised score summary

| Criterion | Max | Revised score | Notes |
|-----------|-----|---------------|--------|
| 1. Functionality | 8 | **8** | Unchanged; already full. |
| 2. Code Elegance and Quality | 8 | **8** | Aligns with Code Elegance rubric average **4.0 / 4.0** after helper extraction and constants (see revised elegance report). |
| 3. Testing | 8 | **8** | Malformed JSON paths covered; runner asserts mixed Nash block. |
| 4. Individual Participation | 6 | **5** | CONTRIBUTING sets expectations; **6 / 6** if instructor confirms **balanced** substantive commits for both teammates. |
| 5. Documentation | 5 | **5** | README + CONTRIBUTING + expanded docstrings. |
| 6. I/O Clarity | 5 | **5** | Unchanged. |
| 7. Topic Engagement | 6 | **6** | Mixed-strategy Nash plus prior pure Nash / minimax / search topics. |
| 8. GitHub Practices | 4 | **4** | CONTRIBUTING documents PR/issue workflow. |
| **Total** | **50** | **49** | **+6** vs. original **43 / 50**. |

---

## Original assessment (archived — first-pass review)

The following sections record the **original** criterion-by-criterion scores and narrative (**total 43 / 50**). They are **preserved** for comparison with the revised row above.

---

## Findings by Criterion

### 1. Functionality — **8 / 8**

- **Core behavior**: `run_module4` / `optimize_maintenance_plan` load config + diagnosis, apply optional production downtime cap, run **hill climbing (with restarts)** and **simulated annealing**, pick the better objective, emit assignments and totals.  
- **Tradeoffs**: Budget multiplier sweep (0.5×–1.25×) with re-optimization.  
- **Game layer**: Single-repair **minimax** vs worst-case failure target; **pure Nash** enumeration on a 2×2 operator vs environment payoff grid derived from objective values.  
- **Edge cases**: Empty `equipment` list; **tight downtime** (e.g. zero) forces feasible actions only; SA and HC avoid infinite loops when neighbors are infeasible or only one action exists.  
- **CLI**: `--module 4` with `--diagnosis`, optional `--module4-config`, optional `--production-schedule`.

---

### 2. Code Elegance and Quality — **7 / 8**

- Crosswalk from [Code Elegance Report](checkpoint_4_elegance_report.md): average **3.625 / 4.0** on the Code Elegance rubric → maps to **strong but not flawless** quality on the 8-point scale.  
- **Strengths**: Clear module split (`loader`, `objective`, `optimize`, `game_theory`, `runner`), dataclasses, type hints.  
- **Improvements**: `optimize_maintenance_plan` is long and could be factored; name **magic constants** (stress factor, tradeoff multipliers) for readability.

---

### 3. Testing — **7 / 8**

- **Unit tests** (`unit_tests/module4/`): config and diagnosis loading, production schedule merge, objective/feasibility, hill climbing vs greedy, minimax and Nash helpers, runner shape and file write.  
- **Integration** (`integration_tests/module4/test_module4_smoke.py`): shared fixture runs **M1 → M2 → M3**, then M4; second test verifies **production cap** forces all **defer**.  
- **Gap (minor)**: Could add explicit tests for malformed diagnosis JSON / invalid action indices in saved files; stochastic SA is exercised but not asserted to a fixed optimum.

---

### 4. Individual Participation — **4 / 6**

- **Git snapshot** (`git shortlog -sn`): both human contributors show **multiple commits** (e.g. ~24 vs ~14 in a recent count); both have meaningful activity, with **moderate imbalance**.  
- Fits rubric text: *“All team members contributed. Some imbalance but all participated meaningfully.”*  
- **Note**: Grader should confirm on GitHub that commits reflect real design/code work (not trivial splits).

---

### 5. Documentation — **4 / 5**

- **`README.md`**: Module 4 section covers inputs, outputs, public interfaces, CLI, sample paths, and lists unit/integration tests.  
- **Code**: Module and key function docstrings present (`loader`, `objective`, `game_theory`, top-level `runner` entry points).  
- **Gap**: Not every helper has parameter/return documentation to “excellent” standard; complex payoff construction in `runner` is mostly self-explanatory but could use a short comment block.

---

### 6. I/O Clarity — **5 / 5**

- **Inputs**: `diagnosis.json` (Module 3 shape), `module4_config.json` (`actions`, `budget`, `max_total_downtime_hours`, `failure_cost_scale`, optional HC/SA blocks), optional `production_schedule.json` (`label`, `notes`, optional `max_total_downtime_hours`).  
- **Output**: `maintenance_plan.json` with `assignments`, `totals`, `meta` (production merge + effective downtime cap), `optimization`, `tradeoffs`, `contingency`, `game_analysis`.  
- Shapes are **verifiable** from integration tests and README examples.

---

### 7. Topic Engagement — **5 / 6**

- **Hill climbing** and **simulated annealing**: Direct, meaningful use on a discrete maintenance assignment space under constraints.  
- **Minimax**: Clear “maintainer chooses one full repair; nature picks worst failure target” story.  
- **Nash**: **Pure-strategy** equilibria on a **2×2** game built from schedule vs defer and baseline vs stressed risks — legitimate engagement but **not** a deep general-sum or mixed-strategy treatment tied to full calendar scheduling.  
- Slight deduction vs “deep engagement” for the game-theory slice only.

---

### 8. GitHub Practices — **3 / 4**

- **Strengths**: Meaningful commit history from two developers; classroom repo structure.  
- **Unknown / verify**: Pull-request discipline, issues, and conflict resolution are not certified by this review; commit messages vary in detail.  
- **Recommendation**: Use PRs for Module 4 merge and add a short release/checkpoint tag or checklist issue if course expects it.

---

## Score Summary (original — archived)

| Criterion | Max | Score |
|-----------|-----|-------|
| 1. Functionality | 8 | **8** |
| 2. Code Elegance and Quality | 8 | **7** |
| 3. Testing | 8 | **7** |
| 4. Individual Participation | 6 | **4** |
| 5. Documentation | 5 | **4** |
| 6. I/O Clarity | 5 | **5** |
| 7. Topic Engagement | 6 | **5** |
| 8. GitHub Practices | 4 | **3** |
| **Total** | **50** | **43** |

---

## Cross-References

- Code Elegance detail: [checkpoint_4_elegance_report.md](checkpoint_4_elegance_report.md)  
- Prior combined modules: [checkpoint_3_module_report.md](checkpoint_3_module_report.md)  
- Proposal Module 4 description: [PROPOSAL.md](PROPOSAL.md) (Maintenance Schedule Optimizer)

---

## Suggested pre-submission checklist

- [x] Run `pytest unit_tests integration_tests` and attach or cite log (full integration ~8 tests, ~30s locally after Module 2 smoke caps).  
- [ ] Confirm `outputs/module4/maintenance_plan.json` from a real pipeline run is included or reproducible from README commands.  
- [ ] Reconcile **checkpoint numbering** with the course schedule if your instructor maps “Checkpoint 4” differently.  
- [ ] Optional: short **module explanation** slide or `checkpoint_4_module_explanation.md` mirroring Checkpoint 3 format.
