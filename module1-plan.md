---
name: module-1-setup-and-structure
overview: Prepare the repository and project structure to begin implementing Module 1 (Basic Rule-Based Monitoring) in Python with pytest tests, based on the proposal and course project instructions.
todos:
  - id: update-readme-module1-spec
    content: Fill in README.md with a clear Module 1 spec section and ensure the Module Plan table includes the correct entry for Module 1.
    status: completed
  - id: sync-agents-module-plan
    content: Update AGENTS.md with the current module plan table and project context (title, theme, proposal reference).
    status: pending
  - id: create-src-structure-module1
    content: Create the Python package structure under src/ for equipment_monitoring and module1, including empty module files for config, rules, classifier, io, and CLI.
    status: pending
  - id: create-tests-structure-module1
    content: Create unit_tests/module1 and integration_tests/module1 directories with placeholder pytest files for Module 1.
    status: pending
  - id: define-dependencies-and-doc-env
    content: Add Python dependency metadata (requirements.txt or pyproject.toml) and document setup steps in README.md.
    status: pending
  - id: specify-data-formats-and-interfaces
    content: Document JSON/CSV input and JSON/text output schemas for Module 1 and define the main public API functions to be used by later modules.
    status: pending
  - id: design-test-cases-module1
    content: Write down the unit and integration test scenarios for Module 1 in README.md, aligned with the rubric and project instructions.
    status: pending
isProject: false
---

## Module 1 Context

- **Module 1 goal**: "Basic Rule-Based Monitoring" using propositional logic to classify each sensor reading as normal or anomaly, given configuration and equipment specs.
- **Inputs (from `PROPOSAL.md`)**:
- Configuration JSON of allowed ranges per metric (temperature, vibration, pressure, etc.).
- Sensor readings CSV with columns `timestamp, temperature, vibration, pressure` (numeric).
- Equipment specification JSON with normal operating ranges per equipment type.
- **Outputs**:
- Per-reading JSON classifications with status, violated rules, and confidence.
- Human-readable alert messages summarizing anomalies.
- **Project-wide constraints** (from `PROPOSAL.md` and `AGENTS.md`):
- Use 5–6 modules total, each with clear inputs/outputs and tests.
- Keep `src/`, `unit_tests/`, and `integration_tests/` aligned with the overall repository layout.
- For each module, write a short spec in `README.md`, get an approved plan, then implement and test.

## Repository Structure To Establish Now

- **Top-level Python project layout** (fill in what is missing):
- [`src`](src/) — main Python package code.
- [`unit_tests`](unit_tests/) — pytest unit tests mirroring `src/` structure.
- [`integration_tests`](integration_tests/) — integration tests; for Module 1 this can be stubbed but will be more relevant from Module 2 onward.
- Add typical Python support files:
- `requirements.txt` (or `pyproject.toml`) for dependencies.
- `README.md` updated with module specs and basic run/test instructions.
- Optional `setup.cfg` or `pyproject.toml` for pytest configuration.

- **Suggested Python package structure for Module 1** (within `src/`):
- `src/equipment_monitoring/__init__.py` — package root.
- `src/equipment_monitoring/module1/__init__.py` — Module 1 namespace.
- `src/equipment_monitoring/module1/config.py` — loading and validating JSON config/specs.
- `src/equipment_monitoring/module1/rules.py` — propositional rules & rule evaluation logic.
- `src/equipment_monitoring/module1/classifier.py` — high-level per-reading classification API.
- `src/equipment_monitoring/module1/io.py` — CSV/JSON I/O helpers for reading sensor data and writing outputs.
- `src/equipment_monitoring/cli.py` — simple CLI entrypoint to run Module 1 on example data.

- **Tests structure**:
- `unit_tests/module1/test_config.py` — tests for config/spec loading and edge cases (missing fields, invalid ranges).
- `unit_tests/module1/test_rules.py` — tests for rule evaluation on synthetic readings.
- `unit_tests/module1/test_classifier.py` — end-to-end per-reading classification tests.
- `unit_tests/module1/test_io.py` — tests for CSV/JSON I/O functions (using small fixtures).
- `integration_tests/` — initially, can contain a simple `module1/` smoke test that runs the CLI against a small sample CSV + config and checks outputs, even if more complex integration is deferred to later modules.

## Preparation Steps Before Coding Module 1

- **1. Document the Module 1 spec in `README.md`**
- Add Module 1 to the "Module Plan" table in [`README.md`](README.md) (or fill in the existing row) using the inputs/outputs already written in `PROPOSAL.md`.
- Under a new `## Module 1: Basic Rule-Based Monitoring` section, briefly restate:
- Inputs (files, formats, example schemas).
- Outputs (JSON record shape and alert text style).
- Assumptions (e.g., all units are SI; timestamps ISO-8601; missing values handling strategy).
- Testing plan (unit tests in `unit_tests/module1/`, optional initial integration test).

- **2. Sync `AGENTS.md` with the plan**
- Populate the "Module plan" section in [`AGENTS.md`](AGENTS.md) by copying the Module Plan table from `README.md`.
- Ensure `System title`, `Theme`, and `Proposal link or summary` reference this industrial equipment monitoring project and `PROPOSAL.md`.

- **3. Create the code and test directory skeletons**
- Under `src/`, create the `equipment_monitoring/` package and `module1/` subpackage with the empty Python files listed above.
- Under `unit_tests/`, create the `module1/` directory and corresponding empty `test_*.py` modules.
- Under `integration_tests/`, create `module1/` with a placeholder test file (e.g., `test_module1_smoke.py`) that will later run the full Module 1 pipeline on a small dataset.

- **4. Decide and declare dependencies + environment**
- Choose a minimal baseline for Module 1 (e.g., just Python standard library + `pytest`).
- List these in `requirements.txt` or `pyproject.toml` and update [`README.md`](README.md) with:
- Python version requirement.
- How to create and activate a virtual environment.
- `pip install -r requirements.txt` (or equivalent) instructions.

- **5. Define the external data formats clearly**
- In `README.md` or a dedicated doc (e.g., `docs/module1_data.md` if you like), specify:
- Exact JSON config schema (keys, types, optional vs required, example file).
- Exact equipment-spec JSON schema.
- CSV schema with an example snippet.
- Expected JSON output record structure, including naming conventions for `violated_rules` and `confidence` range/meaning.
- Optionally check these against the course project instructions and rubric (`ai-system.project.md`, `ai-system.rubric.md`) to ensure clarity and reproducibility.

- **6. Establish a basic CLI/run workflow for Module 1**
- Decide on a single entrypoint script, e.g. `python -m equipment_monitoring.cli` or `python src/equipment_monitoring/cli.py`.
- In `README.md`, add a short "Running Module 1" section with:
- Command-line example using a sample config, specs, and CSV.
- Description of where outputs are written (e.g., `outputs/module1/classifications.json` and `outputs/module1/alerts.txt`).

- **7. Define the initial test plan for Module 1**
- In the Module 1 section of `README.md`, list:
- Unit-test cases (e.g., threshold boundary checks, multiple violations, no violations, malformed input).
- A smoke-test scenario that runs the full pipeline on a tiny synthetic dataset and asserts:
- Number of anomalies detected.
- Presence of specific `violated_rules` tags.
- Ensure this aligns with the rubric emphasis on clear tests and evidence at Checkpoint 1.

## How This Sets Up Future Modules

- **Stable public interfaces**:
- Module 1 will expose functions like `classify_reading(reading, config, specs)` and `run_module1(config_path, specs_path, csv_path)` from `equipment_monitoring.module1.classifier`, which later modules (search, diagnosis, etc.) can call.
- **Data artifacts for later modules**:
- Decide and document where Module 1 writes its anomaly-enriched outputs (e.g., `data/module1/annotated_readings.csv`), so Module 2 can consume them as "historical sensor data with failure events".
- **Consistent directory and test organization**:
- The `module1` layout becomes the pattern for `module2`, `module3`, etc., simplifying future expansion and keeping the project aligned with the course instructions and rubric.
