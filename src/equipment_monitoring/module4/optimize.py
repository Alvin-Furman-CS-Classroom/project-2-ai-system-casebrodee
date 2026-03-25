"""Hill climbing and simulated annealing over discrete maintenance assignments."""

from __future__ import annotations

import math
import random
from typing import List, Tuple

from .loader import EquipmentRisk, MaintenanceAction, Module4Config
from .objective import Assignment, evaluate_objective, schedule_feasible


def _random_feasible(
    n: int,
    n_actions: int,
    actions: Tuple[MaintenanceAction, ...],
    budget: float,
    max_downtime: float,
    max_tries: int = 5000,
) -> Assignment | None:
    for _ in range(max_tries):
        vec = tuple(random.randrange(n_actions) for _ in range(n))
        if schedule_feasible(vec, actions, budget, max_downtime):
            return vec
    return None


def hill_climb(
    equipment: List[EquipmentRisk],
    config: Module4Config,
    start: Assignment,
) -> Tuple[Assignment, float, int]:
    """
    First-improvement hill climbing over single-position action changes.

    Args:
        equipment: Risk profile per slot (same order as assignment indices).
        config: Budget, downtime cap, failure scale, and iteration budget.
        start: Feasible starting assignment (action index per equipment).

    Returns:
        (best_assignment, best_objective, neighbor_evaluations_count).
    """
    actions = config.actions
    n = len(equipment)
    n_act = len(actions)
    current = start
    _, _, cur_obj = evaluate_objective(current, equipment, actions, config.failure_cost_scale)
    iterations = 0
    max_it = config.hill_climbing_max_iterations

    while iterations < max_it:
        improved = False
        for pos in range(n):
            for new_a in range(n_act):
                if new_a == current[pos]:
                    continue
                iterations += 1
                nxt = list(current)
                nxt[pos] = new_a
                cand = tuple(nxt)
                if not schedule_feasible(cand, actions, config.budget, config.max_total_downtime_hours):
                    continue
                _, _, obj = evaluate_objective(cand, equipment, actions, config.failure_cost_scale)
                if obj < cur_obj - 1e-12:
                    current = cand
                    cur_obj = obj
                    improved = True
                    break
            if improved:
                break
        if not improved:
            break

    return current, cur_obj, iterations


def hill_climb_with_restarts(
    equipment: List[EquipmentRisk],
    config: Module4Config,
    greedy_start: Assignment,
) -> Tuple[Assignment, float, int, dict]:
    """
    Hill climb from a greedy seed plus random feasible restarts; keep best objective.

    Returns:
        (best_assignment, best_objective, total_iterations, metadata dict).
    """
    best = greedy_start
    _, _, best_obj = evaluate_objective(best, equipment, config.actions, config.failure_cost_scale)
    total_iter = 0
    for r in range(config.hill_climbing_restarts):
        if r == 0:
            start = greedy_start
        else:
            rnd = _random_feasible(
                len(equipment),
                len(config.actions),
                config.actions,
                config.budget,
                config.max_total_downtime_hours,
            )
            start = rnd if rnd is not None else greedy_start
        cand, obj, it = hill_climb(equipment, config, start)
        total_iter += it
        if obj < best_obj:
            best, best_obj = cand, obj
    meta = {"restarts_used": config.hill_climbing_restarts, "iterations": total_iter}
    return best, best_obj, total_iter, meta


def simulated_anneal(
    equipment: List[EquipmentRisk],
    config: Module4Config,
    start: Assignment,
) -> Tuple[Assignment, float, int]:
    """
    Simulated annealing with random single-position moves and feasibility filter.

    Returns:
        (best_assignment_found, its_objective, iterations_run).
    """
    actions = config.actions
    n = len(equipment)
    n_act = len(actions)
    if n_act <= 1 or n == 0:
        _, _, obj = evaluate_objective(start, equipment, actions, config.failure_cost_scale)
        return start, obj, 0
    current = start
    _, _, cur_obj = evaluate_objective(current, equipment, actions, config.failure_cost_scale)
    best, best_obj = current, cur_obj
    T = config.sa_initial_temp
    iterations = 0
    max_it = config.sa_max_iterations

    while iterations < max_it:
        iterations += 1
        pos = random.randrange(n)
        new_a = random.randrange(n_act)
        if new_a != current[pos]:
            nxt = list(current)
            nxt[pos] = new_a
            cand = tuple(nxt)
            if schedule_feasible(cand, actions, config.budget, config.max_total_downtime_hours):
                _, _, obj = evaluate_objective(cand, equipment, actions, config.failure_cost_scale)
                delta = obj - cur_obj
                if delta < 0 or (T > 1e-12 and random.random() < math.exp(-delta / T)):
                    current = cand
                    cur_obj = obj
                    if obj < best_obj:
                        best, best_obj = cand, obj
        T *= config.sa_cooling_rate
        if T < 1e-12:
            T = 1e-12

    return best, best_obj, iterations
