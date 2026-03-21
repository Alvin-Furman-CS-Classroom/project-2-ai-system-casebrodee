# Checkpoint 3 — Module Explanation (In-Person Demo Guide)

**Scope**: End-to-end pipeline **Module 1 → Module 2 → Module 3**  
**Primary new topic (Checkpoint focus)**: **Module 3** — First-order style knowledge base, unification, forward chaining  
**Repository**: [https://github.com/Alvin-Furman-CS-Classroom/project-2-ai-system-casebrodee](https://github.com/Alvin-Furman-CS-Classroom/project-2-ai-system-casebrodee)  
**Date**: March 21, 2026

Use this document with [checkpoint_preparation.md](checkpoint_preparation.md) §2 (input / output / AI concepts) and §3 (slide ideas). **Authoritative I/O and CLI** for graders and setup: [README.md](README.md) (Module 3 section and “Running Modules”).

---

## 1. Pipeline placement (where Module 3 sits)

```
Readings CSV ──► Module 1 ──► classifications.jsonl ──┐
       │                                │              ├──► Module 3 ──► diagnosis.json
       └──────────────────────────────► Module 2 ──► sequences.json, warning_signs.json ──┘
```

- **Module 1** flags per-reading anomalies and rule violations.  
- **Module 2** finds historical failure sequences and ranked warning signs (graph + search).  
- **Module 3** combines those signals with a **declarative KB** to produce **hypotheses**, **scores**, **explanation chains**, and **inspection** text.

---

## 2. Module 3 — Input

### What does Module 3 accept?

1. **Knowledge base JSON** (`kb.json`)  
   - **Purpose**: Horn-style rules the instructor/grader can edit without changing Python.  
   - **Variables**: arguments starting with `?` (e.g. `?e` for equipment).  
   - **Shape** (per rule): `id`, `priority`, `antecedents` (list of atoms), `consequent` (one atom), optional `inspection` string.  
   - **Example atom**: `["violated", "?e", "vibration_high"]`  
   - **Example rule** (conceptual): if `violated(?e, vibration_high)` and `m2_on_failure_path(?e)` then `suggests(?e, rotating_component_stress)`.

2. **Module 1 output**: `classifications.jsonl` (one JSON object per line: `equipment_id`, `status`, `violated_rules`, `confidence`, …).

3. **Module 2 outputs** (**required**):  
   - `sequences.json` — discovered sequences + `machines` lists.  
   - `warning_signs.json` — ranked patterns + `predictive_score`, etc.

### Concrete mini-example (facts the code derives per `equipment_id`)

From classifications + sequences + warning signs, the engine emits ground atoms such as:

- `("status", "M1", "anomaly")`  
- `("violated", "M1", "vibration_high")`  
- `("m2_on_failure_path", "M1")`  
- `("m1_max_confidence", "M1", "0.9")`  
- `("m2_top_predictive", "M1", "<score>")`  

(Exact strings depend on your CSV and KB.)

### Constraints

- Module 3 expects **consistent** `equipment_id` strings across M1 rows and M2 `machines` entries for correlation.  
- KB must be valid JSON and pass loader validation (`KnowledgeBaseError` if not).

---

## 3. Module 3 — Output

### What does Module 3 produce?

- **`diagnosis.json`** — object with key `equipment`: array of blocks, one per equipment ID seen in classifications. Each block includes:
  - **`equipment_id`**
  - **`diagnoses`**: ranked list of hypotheses (from `suggests` atoms), each with `hypothesis`, `score`, `supporting_rule_ids`, nested **`explanation`** (fact vs inference tree), **`inspection`** text from the firing rule
  - **`primitive_facts`**: ground facts fed to the engine
  - **`meta`**: M1/M2 summary fields for the demo (confidence, predictive score, path flags)

### Next module feed (Module 4 — preview)

Per `PROPOSAL.md`, **Module 4** consumes **equipment health / failure assessments** and costs. In practice you can treat **`diagnosis.json`** as the structured input: top hypotheses, scores, and recommended inspections become features or constraints for scheduling and optimization—no need to re-run M1/M2 inside M4 if you pass the latest `diagnosis.json` (or a slim JSON you derive from it).

---

## 4. AI concepts (what to say in the demo)

### Techniques

| Module | Concepts |
|--------|----------|
| **1** | Propositional-style rules over sensor thresholds; violations as evidence. |
| **2** | State graph (discretized sensors); **BFS**, **DFS**, **A\***; heuristics (`time_to_failure`, `sensor_distance`). |
| **3** | **Terms and atoms**; **unification** (MGU-style extension on atoms); **substitution**; **forward chaining** to fixpoint with **provenance** for explanations. |

### Why these fit the problem

- **Search (M2)** finds **patterns in historical state space** when you do not have long per-machine time series (similarity edges).  
- **Logic (M3)** turns scattered signals into **auditable recommendations**: every `suggests` conclusion can trace back to **which rules and which facts** fired—important for maintenance decisions and grading “explainability.”

### One sentence pitch

> “We discretize sensors into a graph, search for paths to failure, then **unify** those results with live rule violations in a **forward-chaining** engine so operators get ranked diagnoses with **explanation trees**, not just raw alerts.”

---

## 5. Module 2 updates worth mentioning (if asked)

- **Full graph**: all CSV rows are loaded; similarity mode connects **every** pair of states that differ by exactly one sensor bin (bidirectional edges).  
- **Search caps**: optional `max_total_paths` and `max_paths_per_start` in `search_params.json` (`null` = no cap). This keeps large datasets tractable while the **graph** stays complete.

---

## 6. Presentation quick checklist (from checkpoint_preparation.md §3)

- [ ] **Data flow diagram**: M1 CSV → classifications; same or compatible CSV → M2 graph/search → sequences + warnings; all → M3 → diagnosis.  
- [ ] **Screenshot or live JSON**: one `diagnosis.json` block with `explanation` expanded.  
- [ ] **AI slide**: small rule with `?e`, show substitution to ground facts, then one forward-chaining step.  
- [ ] **Integration slide**: “Module 4 reads assessments from Module 3 output.”

---

## 7. Demo command sequence (project root, `PYTHONPATH=src`)

**Shared CSV** (Module 1 schema + `failure_status`) — adjust paths if needed:

```bash
python -m equipment_monitoring.cli --module 1 \
  --config <path>/config.json --specs <path>/specs.json \
  --readings <path>/readings_with_failures.csv \
  --output-dir outputs/module1

python -m equipment_monitoring.cli --module 2 \
  --data <path>/readings_with_failures.csv \
  --graph-config src/data/module2/graph_config.json \
  --search-params src/data/module2/search_params.json \
  --output-dir outputs/module2 \
  --data-format module1 \
  --classifications outputs/module1/classifications.jsonl

python -m equipment_monitoring.cli --module 3 \
  --kb src/data/module3/kb.json \
  --classifications outputs/module1/classifications.jsonl \
  --sequences outputs/module2/sequences.json \
  --warning-signs outputs/module2/warning_signs.json \
  --output-dir outputs/module3
```

Open **`outputs/module3/diagnosis.json`** for the demo.

---

*Prepared for CSC-343 Checkpoint 3 preparation; rubric-aligned reports: `checkpoint_3_elegance_report.md`, `checkpoint_3_module_report.md`.*
