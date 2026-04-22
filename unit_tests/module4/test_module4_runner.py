"""Tests for Module 4 runner."""

import json
from pathlib import Path

from equipment_monitoring.module4.runner import optimize_maintenance_plan, run_module4


def test_optimize_maintenance_plan_shape(tmp_path: Path) -> None:
    diag = tmp_path / "diagnosis.json"
    diag.write_text(
        json.dumps(
            {
                "equipment": [
                    {
                        "equipment_id": "M1",
                        "diagnoses": [{"hypothesis": "x", "score": 0.7}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cfg = tmp_path / "m4.json"
    cfg.write_text(
        json.dumps(
            {
                "actions": [
                    {"id": "defer", "cost": 0, "downtime_hours": 0, "risk_multiplier": 1.0},
                    {"id": "inspect", "cost": 50, "downtime_hours": 1, "risk_multiplier": 0.5},
                ],
                "budget": 100,
                "max_total_downtime_hours": 5,
                "failure_cost_scale": 500,
                "hill_climbing": {"max_iterations": 300, "restarts": 2},
                "simulated_annealing": {"initial_temp": 1.0, "cooling_rate": 0.99, "max_iterations": 300},
            }
        ),
        encoding="utf-8",
    )
    plan = optimize_maintenance_plan(diag, cfg)
    assert "assignments" in plan
    assert len(plan["assignments"]) == 1
    assert plan["assignments"][0]["equipment_id"] == "M1"
    assert "optimization" in plan
    assert "tradeoffs" in plan
    assert "contingency" in plan
    assert "game_analysis" in plan
    assert "mixed_nash_zero_sum_row_matrix" in plan["game_analysis"]
    assert "equilibrium" in plan["game_analysis"]["mixed_nash_zero_sum_row_matrix"]
    assert "meta" in plan
    assert plan["meta"]["production_schedule"]["applied"] is False


def test_run_module4_writes_file(tmp_path: Path) -> None:
    diag = tmp_path / "diagnosis.json"
    diag.write_text(
        json.dumps({"equipment": [{"equipment_id": "Z", "diagnoses": [{"score": 0.2}]}]}),
        encoding="utf-8",
    )
    cfg = tmp_path / "m4.json"
    cfg.write_text(
        json.dumps(
            {
                "actions": [{"id": "defer", "cost": 0, "downtime_hours": 0, "risk_multiplier": 1.0}],
                "budget": 0,
                "max_total_downtime_hours": 0,
                "failure_cost_scale": 100,
                "hill_climbing": {"max_iterations": 20, "restarts": 1},
                "simulated_annealing": {
                    "initial_temp": 0.5,
                    "cooling_rate": 0.99,
                    "max_iterations": 30,
                },
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    run_module4(diag, cfg, out)
    assert (out / "maintenance_plan.json").is_file()
