# Industrial equipment monitoring — full stack from repo-root demo data.
# Requires: Python 3 with project deps; run from repository root.
# Override paths: make pipeline M1_READINGS=/path/to.csv
#
# Python: if ./.venv/bin/python exists (e.g. after: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt),
# it is used by default so `make test` finds pytest without a global install.

.PHONY: help test typecheck pipeline report summary m1 m2 m3 m4 m6

PYTHON_VENV := $(wildcard .venv/bin/python)
PYTHON ?= $(if $(PYTHON_VENV),$(PYTHON_VENV),python3)
PY := PYTHONPATH=src $(PYTHON) -m equipment_monitoring.cli

# Unified outputs tree (report reads outputs/module*/…)
OUT := outputs

# Bundled Module-1–compatible CSV + config (see README “Full pipeline”)
PIPELINE_DATA ?= $(OUT)/full_pipeline/data
M1_CONFIG ?= $(PIPELINE_DATA)/config.json
M1_SPECS ?= $(PIPELINE_DATA)/specs.json
M1_READINGS ?= $(PIPELINE_DATA)/readings_with_failures.csv

GRAPH_CFG ?= src/data/module2/graph_config.json
SEARCH_PARAMS ?= src/data/module2/search_params.json
KB ?= src/data/module3/kb.json
M4_CFG ?= src/data/module4/module4_config.json
PROD_SCHED ?= src/data/module4/production_schedule.json

help:
	@echo "Targets:"
	@echo "  make test       — pytest on unit_tests/ and integration_tests/ (uses .venv if present; else PYTHON)"
	@echo "  make typecheck  — mypy on module6 + reporting (see pyproject.toml; needs: pip install -r requirements.txt)"
	@echo "  make pipeline   — Module 1→2→3→4→6 then regenerate outputs/report.html"
	@echo "  make report     — Regenerate outputs/report.html from current outputs/"
	@echo "  make summary    — Write outputs/fleet_summary.json from current outputs/ (no module re-run)"
	@echo "  make m1 … m6    — Run a single module (same paths as pipeline)"
	@echo "Variables: PIPELINE_DATA, M1_CONFIG, M1_SPECS, M1_READINGS, OUT, PYTHON"

test:
	PYTHONPATH=src $(PYTHON) -m pytest unit_tests integration_tests

typecheck:
	$(PYTHON) -m mypy

report:
	@PYTHONPATH=src $(PYTHON) -c 'from pathlib import Path; from equipment_monitoring.reporting import generate_report; generate_report(Path("$(OUT)"), Path("$(OUT)/report.html"))'
	@echo "Wrote $(OUT)/report.html"

summary:
	@PYTHONPATH=src $(PYTHON) -c 'from pathlib import Path; from equipment_monitoring.reporting import write_fleet_summary; write_fleet_summary(Path("$(OUT)"))'
	@echo "Wrote $(OUT)/fleet_summary.json"

m1:
	$(PY) --module 1 \
		--config $(M1_CONFIG) \
		--specs $(M1_SPECS) \
		--readings $(M1_READINGS) \
		--output-dir $(OUT)/module1

m2: m1
	$(PY) --module 2 \
		--data $(M1_READINGS) \
		--graph-config $(GRAPH_CFG) \
		--search-params $(SEARCH_PARAMS) \
		--output-dir $(OUT)/module2 \
		--data-format module1 \
		--classifications $(OUT)/module1/classifications.jsonl

m3: m2
	$(PY) --module 3 \
		--kb $(KB) \
		--classifications $(OUT)/module1/classifications.jsonl \
		--sequences $(OUT)/module2/sequences.json \
		--warning-signs $(OUT)/module2/warning_signs.json \
		--output-dir $(OUT)/module3

m4: m3
	$(PY) --module 4 \
		--diagnosis $(OUT)/module3/diagnosis.json \
		--module4-config $(M4_CFG) \
		--production-schedule $(PROD_SCHED) \
		--output-dir $(OUT)/module4

m6: m4
	$(PY) --module 6 \
		--diagnosis $(OUT)/module3/diagnosis.json \
		--classifications $(OUT)/module1/classifications.jsonl \
		--output-dir $(OUT)/module6

pipeline: m6 report
