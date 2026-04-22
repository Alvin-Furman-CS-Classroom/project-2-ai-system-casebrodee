"""Production schedule JSON and downtime cap merge."""

import json
from pathlib import Path

import pytest

from equipment_monitoring.module4.loader import (
    MaintenanceAction,
    Module4Config,
    Module4ConfigError,
    ProductionSchedule,
    apply_production_downtime_cap,
    load_production_schedule,
)


def _config(max_dt: float = 40.0) -> Module4Config:
    return Module4Config(
        actions=(
            MaintenanceAction("defer", 0, 0, 1.0),
            MaintenanceAction("fix", 10, 1, 0.5),
        ),
        budget=100,
        max_total_downtime_hours=max_dt,
        failure_cost_scale=1000,
        hill_climbing_max_iterations=10,
        hill_climbing_restarts=1,
        sa_initial_temp=1.0,
        sa_cooling_rate=0.99,
        sa_max_iterations=10,
    )


def test_load_production_schedule(tmp_path: Path) -> None:
    p = tmp_path / "p.json"
    p.write_text(
        json.dumps(
            {
                "label": "peak",
                "notes": "test",
                "max_total_downtime_hours": 12,
            }
        ),
        encoding="utf-8",
    )
    s = load_production_schedule(p)
    assert s.label == "peak"
    assert s.max_total_downtime_hours == 12.0


def test_apply_cap_tightens_config() -> None:
    cfg = _config(40.0)
    from equipment_monitoring.module4.loader import ProductionSchedule

    sched = ProductionSchedule("x", "n", 10.0)
    new_c, meta = apply_production_downtime_cap(cfg, sched)
    assert new_c.max_total_downtime_hours == 10.0
    assert meta["effective_max_total_downtime_hours"] == 10.0


def test_apply_cap_no_numeric_uses_base() -> None:
    cfg = _config(25.0)
    sched = ProductionSchedule("x", "n", None)
    new_c, meta = apply_production_downtime_cap(cfg, sched)
    assert new_c.max_total_downtime_hours == 25.0
    assert meta["applied"] is True
    assert meta["cap_source"] == "none"


def test_apply_cap_schedule_looser_than_config_keeps_base() -> None:
    cfg = _config(15.0)
    sched = ProductionSchedule("x", "n", 99.0)
    new_c, meta = apply_production_downtime_cap(cfg, sched)
    assert new_c.max_total_downtime_hours == 15.0
    assert meta["effective_max_total_downtime_hours"] == 15.0


def test_load_rejects_negative_cap(tmp_path: Path) -> None:
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"max_total_downtime_hours": -1}), encoding="utf-8")
    with pytest.raises(Module4ConfigError):
        load_production_schedule(p)
