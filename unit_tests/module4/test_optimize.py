"""Tests for Module 4 optimizers."""

from equipment_monitoring.module4.loader import EquipmentRisk, MaintenanceAction, Module4Config
from equipment_monitoring.module4.objective import evaluate_objective, greedy_initial
from equipment_monitoring.module4.optimize import hill_climb_with_restarts


def test_hill_climb_improves_or_matches_greedy() -> None:
    actions = (
        MaintenanceAction("defer", 0, 0, 1.0),
        MaintenanceAction("inspect", 30, 1, 0.7),
        MaintenanceAction("repair", 120, 4, 0.15),
    )
    cfg = Module4Config(
        actions=actions,
        budget=200,
        max_total_downtime_hours=10,
        failure_cost_scale=800,
        hill_climbing_max_iterations=500,
        hill_climbing_restarts=3,
        sa_initial_temp=1.0,
        sa_cooling_rate=0.995,
        sa_max_iterations=500,
    )
    equipment = [
        EquipmentRisk("A", 0.95),
        EquipmentRisk("B", 0.85),
        EquipmentRisk("C", 0.1),
    ]
    g = greedy_initial(equipment, cfg)
    _, _, g_obj = evaluate_objective(g, equipment, actions, cfg.failure_cost_scale)
    best, obj, _, _ = hill_climb_with_restarts(equipment, cfg, g)
    assert obj <= g_obj + 1e-6
    assert len(best) == len(equipment)
