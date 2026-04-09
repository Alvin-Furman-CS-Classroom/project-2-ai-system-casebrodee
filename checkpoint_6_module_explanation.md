# Checkpoint 6 — Module Explanation (In-Person Demo Guide)

**Scope**: **Module 6** — Reinforcement learning on a maintenance MDP (tabular Q-learning)  
**Pipeline placement**: After **Module 3** (`diagnosis.json`); **Module 4** optional for action validation; **Module 5 skipped** for this path  
**Repository**: [project-2-ai-system-casebrodee](https://github.com/Alvin-Furman-CS-Classroom/project-2-ai-system-casebrodee)  
**Date**: April 9, 2026

Use with [checkpoint_preparation.md](checkpoint_preparation.md) §2 (input / output / AI concepts) and §3 (slide ideas). **Authoritative I/O and CLI**: [README.md](README.md) (Module 6 under “Running Modules”). Rubric reports: [checkpoint_6_module_report.md](checkpoint_6_module_report.md), [checkpoint_6_elegance_report.md](checkpoint_6_elegance_report.md).

---

## 1. Where Module 6 sits

```
Module 3 ──► diagnosis.json ──┬──► Module 4 ──► maintenance_plan.json (optional optimizer)
                              │
                              └──► Module 6 ──► rl_policy.json, rl_training.json, rl_metrics.json
                                        ▲
                                        └── mdp.json + module6_config.json (MDP + hyperparameters)
```

- **Module 6** does **not** re-run M3; it **reads** the same **`diagnosis.json`** Module 4 uses.  
- The **learned policy** is over **aggregate risk states** (`risk_low` / `risk_mid` / `risk_high`), not per-equipment IDs—so it complements Module 4’s **per-equipment** assignment story.

---

## 2. Input (what Module 6 accepts)

### 2.1 `diagnosis.json` (Module 3 output)

- **Role**: Supplies one **scalar risk per equipment** (same rule as Module 4: max **`score`** over diagnoses, or **`meta`** blend if no scores).  
- **Effect**: Each equipment maps to a **risk bucket** using **`risk_thresholds`** in `module6_config.json` (two cut points in `[0, 1]`).  
- **Concrete example** (conceptual):

```json
{
  "equipment": [
    { "equipment_id": "M1", "diagnoses": [{ "hypothesis": "stress", "score": 0.74 }] },
    { "equipment_id": "M2", "diagnoses": [{ "hypothesis": "watch", "score": 0.45 }] }
  ]
}
```

With thresholds `[0.33, 0.66]`, buckets might be **`risk_high`** for M1 and **`risk_mid`** for M2.

### 2.2 `module6_config.json`

- **Hyperparameters**: `gamma`, `alpha`, `epsilon_start`, `epsilon_end`, `epsilon_decay_episodes`, `num_episodes`, `max_steps_per_episode`, `random_seed`.  
- **Paths**: `mdp_path` (usually `mdp.json` next to config), optional `module4_config_path` to check MDP **actions** ⊆ Module 4 **actions**.

### 2.3 `mdp.json` (explicit MDP)

- **`states`**, **`actions`**, **`transitions[state][action]`** = list of **`[probability, next_state, reward]`** (probabilities sum to 1).  
- **`initial_state_weights`**: required if **`diagnosis.json`** has **no** equipment rows—otherwise episodes cannot start.

### Constraints

- Bucket names from thresholds must match **`mdp.json`** `states`.  
- MDP should include **`defer`** if you want the **always-defer baseline** in `rl_metrics.json`.

---

## 3. Output (what Module 6 produces)

### 3.1 `rl_policy.json`

- **`policy`**: map **risk state → action id** (greedy w.r.t. learned Q).  
- **`q_table`**: full table for transparency.  
- **`meta`**: paths, seed, hyperparameters, `module5_required: false`, training narrative.

### 3.2 `rl_training.json`

- **`episodes`**: each episode’s **return**, **ε**, **steps**, **cumulative mean return**.  
- **Use in demo**: show **learning curve** (returns or mean-so-far vs episode).

### 3.3 `rl_metrics.json`

- **`trained_policy_last_window`**: mean/std return over last **N** episodes.  
- **`baseline_always_defer`** / **`baseline_random`**: same horizon, fixed policies—**compare** to learned behavior.  
- **`mdp`**: state/action counts for a one-line sanity check.

### Next module / “final output”

- There is **no Module 7** in the plan; Module 6 is a **final policy artifact** for **operations or reporting**.  
- **Optional narrative**: “Operators can compare **RL suggested action by risk tier** with **Module 4’s per-machine plan** under budget constraints.”

---

## 4. AI concepts (what to say in the demo)

### Techniques

| Concept | Where it shows up |
|--------|-------------------|
| **MDP** | `mdp.json`: finite **S**, **A**, **P(s′\|s,a)**, **rewards** read explicitly—no black-box env. |
| **Q-learning** | Tabular update: \(Q(s,a) \leftarrow Q(s,a) + \alpha [ r + \gamma \max_{a'} Q(s',a') - Q(s,a) ]\). |
| **Exploration / exploitation** | **ε-greedy** action selection; **linear ε decay** over episodes. |
| **Policy** | **Greedy** policy from final Q-table. |
| **Evaluation** | **Monte Carlo-style** episode returns; baselines for context. |

### Why these fit the problem

- Maintenance decisions are often modeled as **sequential stochastic** problems (risk evolves; actions cost money).  
- A **JSON MDP** keeps the model **inspectable** for grading and demos (you can point to transition rows).  
- **Tabular** RL is appropriate for the **small** state space (three risk buckets) and matches **course-scale** RL without neural networks.

### One-sentence pitch

> “We turn Module 3 risks into three buckets, then **learn a Q-table** from **rollouts** of an explicit **JSON MDP** so we get a **state → maintenance action** policy—with **training traces** and **baselines** so we can argue the agent actually improved over **always defer**.”

---

## 5. Slide ideas ([checkpoint_preparation.md](checkpoint_preparation.md) §3)

1. **Data flow**: Box `diagnosis.json` → “bucketize risk” → “simulate MDP” → `rl_policy.json`.  
2. **I/O screenshot**: One **`mdp.json`** transition row + one line from **`rl_policy.json`**.  
3. **Algorithm**: Small diagram: choose action (ε-greedy) → sample `(s′, r)` → Q-update → repeat.  
4. **Integration**: Full pipeline strip M1→M2→M3→(M4)→M6 with Module 6 highlighted.  
5. **Chart**: `return_mean_so_far` vs episode from **`rl_training.json`**.

---

## 6. Demo checklist (quick)

- [ ] Show **`mdp.json`** structure (states, actions, one transition list).  
- [ ] Show **`diagnosis.json`** snippet and which bucket a machine falls into.  
- [ ] Run or show CLI: `--module 6 --diagnosis … --output-dir …`.  
- [ ] Open **`rl_policy.json`** and **`rl_metrics.json`**; compare **mean return** to **baseline_always_defer**.  
- [ ] State clearly: **Module 5 not used**; optional future: add features from a classifier into the state.
