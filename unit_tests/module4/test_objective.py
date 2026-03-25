"""Tests for Module 4 objective and feasibility."""

from equipment_monitoring.module4.loader import EquipmentRisk, MaintenanceAction, Module4Config
from equipment_monitoring.module4.objective import evaluate_objective, schedule_feasible


def _tiny_config() -> Module4Config:
    actions = (
        MaintenanceAction("defer", 0, 0, 1.0),
        MaintenanceAction("fix", 50, 1, 0.5),
    )
    return Module4Config(
        actions=actions,
        budget=100,
        max_total_downtime_hours=5,
        failure_cost_scale=1000,
        hill_climbing_max_iterations=100,
        hill_climbing_restarts=2,
        sa_initial_temp=1.0,
        sa_cooling_rate=0.99,
        sa_max_iterations=200,
    )


def test_schedule_feasible_rejects_bad_index() -> None:
    actions = (MaintenanceAction("a", 0, 0, 1.0),)
    assert not schedule_feasible((5,), actions, 10, 10)


def test_evaluate_objective() -> None:
    cfg = _tiny_config()
    eq = [EquipmentRisk("M1", 0.8), EquipmentRisk("M2", 0.2)]
    assign = (1, 0)
    mc, fp, total = evaluate_objective(assign, eq, cfg.actions, cfg.failure_cost_scale)
    assert mc == 50
    assert fp == 1000 * (0.8 * 0.5 + 0.2 * 1.0)
    assert total == mc + fp
