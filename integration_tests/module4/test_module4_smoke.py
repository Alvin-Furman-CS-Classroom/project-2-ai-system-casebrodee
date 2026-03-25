"""End-to-end: Module 1 -> Module 2 -> Module 3 -> Module 4 on shared CSV."""

import json
from pathlib import Path

import pytest

from equipment_monitoring.module1 import classifier
from equipment_monitoring.module2 import runner as module2_runner
from equipment_monitoring.module3 import runner as module3_runner
from equipment_monitoring.module4 import runner as module4_runner


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).parent.parent.parent


@pytest.fixture
def diagnosis_path(tmp_path: Path, repo_root: Path) -> Path:
    kb_path = repo_root / "src" / "data" / "module3" / "kb.json"
    graph_config_path = repo_root / "src" / "data" / "module2" / "graph_config.json"
    search_params_path = repo_root / "src" / "data" / "module2" / "search_params.json"

    if not kb_path.exists() or not graph_config_path.exists():
        pytest.skip("Module 2/3 data files not found")

    cfg_path = tmp_path / "config.json"
    specs_path = tmp_path / "specs.json"
    csv_path = tmp_path / "readings_with_failures.csv"
    module1_output = tmp_path / "module1_out"
    module2_output = tmp_path / "module2_out"
    module3_output = tmp_path / "module3_out"

    cfg_path.write_text(
        json.dumps(
            {
                "temperature": {"min": 20.0, "max": 80.0},
                "vibration": {"max": 5.0},
                "pressure": {"min": 10.0, "max": 50.0},
            }
        ),
        encoding="utf-8",
    )
    specs_path.write_text("{}", encoding="utf-8")

    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure,failure_status\n"
        "2026-01-01T00:00:00Z,M1,25,1.0,100,0\n"
        "2026-01-01T00:01:00Z,M1,35,2.0,150,0\n"
        "2026-01-01T00:02:00Z,M1,45,4.0,250,0\n"
        "2026-01-01T00:03:00Z,M1,65,5.5,400,1\n"
        "2026-01-01T00:00:00Z,M2,22,1.5,120,0\n"
        "2026-01-01T00:01:00Z,M2,40,3.0,200,0\n"
        "2026-01-01T00:02:00Z,M2,60,5.0,380,1\n",
        encoding="utf-8",
    )

    classifier.run_module1(
        config_path=cfg_path,
        specs_path=specs_path,
        csv_path=csv_path,
        output_dir=module1_output,
    )

    module2_runner.run_module2(
        data_path=csv_path,
        graph_config_path=graph_config_path,
        search_params_path=search_params_path,
        output_dir=module2_output,
        data_format="module1",
        classifications_path=module1_output / "classifications.jsonl",
    )

    module3_runner.run_module3(
        kb_path=kb_path,
        classifications_path=module1_output / "classifications.jsonl",
        sequences_path=module2_output / "sequences.json",
        warning_signs_path=module2_output / "warning_signs.json",
        output_dir=module3_output,
    )

    diag = module3_output / "diagnosis.json"
    assert diag.exists()
    return diag


def _small_module4_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "actions": [
                    {"id": "defer", "cost": 0, "downtime_hours": 0, "risk_multiplier": 1.0},
                    {"id": "inspect", "cost": 100, "downtime_hours": 2, "risk_multiplier": 0.55},
                    {"id": "repair", "cost": 400, "downtime_hours": 8, "risk_multiplier": 0.12},
                ],
                "budget": 2500,
                "max_total_downtime_hours": 40,
                "failure_cost_scale": 3500,
                "hill_climbing": {"max_iterations": 200, "restarts": 2},
                "simulated_annealing": {
                    "initial_temp": 1.0,
                    "cooling_rate": 0.99,
                    "max_iterations": 250,
                },
            }
        ),
        encoding="utf-8",
    )


def test_module1_through_module4_pipeline(diagnosis_path: Path, tmp_path: Path) -> None:
    m4_cfg = tmp_path / "module4_config.json"
    _small_module4_config(m4_cfg)
    out = tmp_path / "module4_out"

    module4_runner.run_module4(
        diagnosis_path=diagnosis_path,
        config_path=m4_cfg,
        output_dir=out,
    )

    plan_path = out / "maintenance_plan.json"
    assert plan_path.is_file()
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    assert "assignments" in plan and len(plan["assignments"]) == 2
    assert "totals" in plan and "objective" in plan["totals"]
    assert "meta" in plan and "production_schedule" in plan["meta"]
    assert plan["meta"]["production_schedule"].get("applied") is False
    for row in plan["assignments"]:
        assert row["equipment_id"] in ("M1", "M2")
        assert "action_id" in row


def test_module4_production_schedule_tightens_downtime(diagnosis_path: Path, tmp_path: Path) -> None:
    m4_cfg = tmp_path / "module4_config.json"
    _small_module4_config(m4_cfg)
    prod = tmp_path / "production_schedule.json"
    prod.write_text(
        json.dumps(
            {
                "label": "zero_downtime_window",
                "max_total_downtime_hours": 0,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "module4_out"

    module4_runner.run_module4(
        diagnosis_path=diagnosis_path,
        config_path=m4_cfg,
        output_dir=out,
        production_schedule_path=prod,
    )

    with open(out / "maintenance_plan.json", encoding="utf-8") as f:
        plan = json.load(f)
    pm = plan["meta"]["production_schedule"]
    assert pm["applied"] is True
    assert pm["effective_max_total_downtime_hours"] == 0
    assert all(a["action_id"] == "defer" for a in plan["assignments"])
