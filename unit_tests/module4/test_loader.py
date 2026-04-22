"""Tests for Module 4 JSON loading."""

import json
from pathlib import Path

import pytest

from equipment_monitoring.module4.loader import (
    Module4ConfigError,
    load_equipment_risks,
    load_module4_config,
    load_production_schedule,
)


def test_load_module4_config_valid(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text(
        json.dumps(
            {
                "actions": [
                    {"id": "defer", "cost": 0, "downtime_hours": 0, "risk_multiplier": 1.0},
                    {"id": "fix", "cost": 100, "downtime_hours": 1, "risk_multiplier": 0.5},
                ],
                "budget": 500,
                "max_total_downtime_hours": 10,
                "failure_cost_scale": 1000,
            }
        ),
        encoding="utf-8",
    )
    cfg = load_module4_config(p)
    assert len(cfg.actions) == 2
    assert cfg.budget == 500.0


def test_load_module4_config_rejects_empty_actions(tmp_path: Path) -> None:
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"actions": [], "budget": 1, "max_total_downtime_hours": 1, "failure_cost_scale": 1}))
    with pytest.raises(Module4ConfigError):
        load_module4_config(p)


def test_load_equipment_risks_from_diagnoses(tmp_path: Path) -> None:
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "equipment": [
                    {"equipment_id": "B", "diagnoses": [{"score": 0.4}, {"score": 0.8}]},
                    {"equipment_id": "A", "diagnoses": [{"score": 0.1}]},
                ]
            }
        ),
        encoding="utf-8",
    )
    risks = load_equipment_risks(p)
    assert [r.equipment_id for r in risks] == ["A", "B"]
    assert risks[0].risk == 0.1
    assert risks[1].risk == 0.8


def test_load_module4_config_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{ not json", encoding="utf-8")
    with pytest.raises(Module4ConfigError) as exc:
        load_module4_config(p)
    assert "not valid JSON" in str(exc.value)


def test_load_equipment_risks_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("[", encoding="utf-8")
    with pytest.raises(Module4ConfigError) as exc:
        load_equipment_risks(p)
    assert "not valid JSON" in str(exc.value)


def test_load_production_schedule_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("undefined", encoding="utf-8")
    with pytest.raises(Module4ConfigError) as exc:
        load_production_schedule(p)
    assert "not valid JSON" in str(exc.value)


def test_load_equipment_risks_meta_fallback(tmp_path: Path) -> None:
    p = tmp_path / "d.json"
    p.write_text(
        json.dumps(
            {
                "equipment": [
                    {
                        "equipment_id": "M1",
                        "diagnoses": [],
                        "meta": {"m1_max_confidence": 0.6, "m2_top_predictive": 0.4},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    risks = load_equipment_risks(p)
    assert risks[0].risk == pytest.approx(0.5)
