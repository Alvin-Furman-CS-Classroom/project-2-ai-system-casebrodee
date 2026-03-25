"""Objective and feasibility for maintenance assignment vectors."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .loader import EquipmentRisk, MaintenanceAction, Module4Config


Assignment = Tuple[int, ...]


def schedule_feasible(
    assignment: Sequence[int],
    actions: Sequence[MaintenanceAction],
    budget: float,
    max_downtime: float,
) -> bool:
    n_act = len(actions)
    for i in assignment:
        if i < 0 or i >= n_act:
            return False
    cost = sum(actions[i].cost for i in assignment)
    down = sum(actions[i].downtime_hours for i in assignment)
    return cost <= budget + 1e-9 and down <= max_downtime + 1e-9


def evaluate_objective(
    assignment: Sequence[int],
    equipment: Sequence[EquipmentRisk],
    actions: Sequence[MaintenanceAction],
    failure_cost_scale: float,
) -> Tuple[float, float, float]:
    """
    Returns (maintenance_cost, failure_penalty, total_objective).
    Failure penalty = failure_cost_scale * sum(risk_i * risk_multiplier(action_i)).
    """
    maint_cost = sum(actions[i].cost for i in assignment)
    penalty = 0.0
    for idx, er in enumerate(equipment):
        mult = actions[assignment[idx]].risk_multiplier
        penalty += er.risk * max(0.0, mult)
    failure_term = failure_cost_scale * penalty
    return maint_cost, failure_term, maint_cost + failure_term


def greedy_initial(
    equipment: List[EquipmentRisk],
    config: Module4Config,
) -> Assignment:
    """Assign higher-risk equipment stronger (lower risk_multiplier) actions while feasible."""
    actions = config.actions
    defer_idx = next((i for i, a in enumerate(actions) if a.id == "defer"), 0)
    n = len(equipment)
    vec = [defer_idx] * n

    order = sorted(range(n), key=lambda i: equipment[i].risk, reverse=True)
    for i in order:
        best_j = defer_idx
        best_obj = evaluate_objective(tuple(vec), equipment, actions, config.failure_cost_scale)[2]
        for j, act in enumerate(actions):
            vec[i] = j
            if not schedule_feasible(vec, actions, config.budget, config.max_total_downtime_hours):
                continue
            obj = evaluate_objective(tuple(vec), equipment, actions, config.failure_cost_scale)[2]
            if obj < best_obj:
                best_obj = obj
                best_j = j
        vec[i] = best_j

    return tuple(vec)
