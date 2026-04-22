"""Module 4 runner: diagnosis.json + config -> maintenance_plan.json."""

from __future__ import annotations

import json
from dataclasses import replace as dc_replace
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .game_theory import (
    minimax_single_full_repair,
    mixed_nash_zero_sum_2x2,
    pure_nash_equilibria_2x2,
)
from .loader import (
    EquipmentRisk,
    Module4Config,
    MaintenanceAction,
    apply_production_downtime_cap,
    load_equipment_risks,
    load_module4_config,
    load_production_schedule,
)
from .objective import evaluate_objective, greedy_initial
from .optimize import hill_climb_with_restarts, simulated_anneal

# Budget multipliers for the tradeoff sweep (relative to configured budget).
TRADEOFF_BUDGET_MULTIPLIERS: Tuple[float, ...] = (0.5, 0.75, 1.0, 1.25)
# Stressed-risk scenario for the 2x2 game column (vs baseline diagnosis-derived risks).
STRESS_RISK_FACTOR = 1.15
SA_VS_HC_EPS = 1e-9
OBJECTIVE_MATCH_EPS = 1e-6


def _defer_only_assignment(n: int, config: Module4Config) -> Tuple[int, ...]:
    defer_idx = next((i for i, a in enumerate(config.actions) if a.id == "defer"), 0)
    return tuple([defer_idx] * n)


def _pick_repair_action(config: Module4Config) -> Tuple[float, float]:
    """Return (cost, risk_multiplier) for the strongest repair-like action (lowest residual risk)."""
    best = min(config.actions, key=lambda a: (a.risk_multiplier, a.cost))
    return best.cost, best.risk_multiplier


def _scale_risks(equipment: List[EquipmentRisk], factor: float) -> List[EquipmentRisk]:
    return [
        EquipmentRisk(e.equipment_id, max(0.0, min(1.0, e.risk * factor))) for e in equipment
    ]


def _assignment_to_rows(
    vec: Tuple[int, ...],
    equipment: List[EquipmentRisk],
    actions: Tuple[MaintenanceAction, ...],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, er in enumerate(equipment):
        act = actions[vec[idx]]
        res_risk = er.risk * act.risk_multiplier
        rows.append(
            {
                "equipment_id": er.equipment_id,
                "action_id": act.id,
                "cost": act.cost,
                "downtime_hours": act.downtime_hours,
                "residual_risk_weighted": round(res_risk, 6),
            }
        )
    return rows


def _run_hill_climb_and_anneal(
    equipment: List[EquipmentRisk],
    config: Module4Config,
) -> Tuple[Tuple[int, ...], float, str, float, Dict[str, Any], int, float]:
    """
    Run greedy seed, hill climbing with restarts, then simulated annealing.

    Returns:
        chosen_assignment, chosen_objective, recommended_method, hc_objective,
        hc_meta, sa_iterations, sa_objective (SA result always reported).
    """
    greedy = greedy_initial(equipment, config)
    hc_best, hc_obj, _, hc_meta = hill_climb_with_restarts(equipment, config, greedy)
    sa_best, sa_obj, sa_it = simulated_anneal(equipment, config, hc_best)
    if sa_obj < hc_obj - SA_VS_HC_EPS:
        return sa_best, sa_obj, "simulated_annealing", hc_obj, hc_meta, sa_it, sa_obj
    return hc_best, hc_obj, "hill_climbing", hc_obj, hc_meta, sa_it, sa_obj


def _budget_tradeoffs(
    equipment: List[EquipmentRisk],
    config: Module4Config,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for mult in TRADEOFF_BUDGET_MULTIPLIERS:
        cfg_b = dc_replace(config, budget=config.budget * mult)
        g = greedy_initial(equipment, cfg_b)
        _, o, _, _ = hill_climb_with_restarts(equipment, cfg_b, g)
        rows.append(
            {
                "budget_multiplier": mult,
                "effective_budget": cfg_b.budget,
                "best_objective": round(o, 4),
            }
        )
    return rows


def _contingency_minimax_block(
    equipment: List[EquipmentRisk],
    config: Module4Config,
) -> Dict[str, Any]:
    repair_cost, repair_mult = _pick_repair_action(config)
    mm = minimax_single_full_repair(
        [e.equipment_id for e in equipment],
        [e.risk for e in equipment],
        repair_cost,
        repair_mult,
        config.failure_cost_scale,
    )
    return {
        "chosen_equipment": mm.chosen_equipment,
        "nature_worst_case_failure_on": mm.worst_case_target,
        "maintainer_repair_cost": mm.maintainer_cost,
        "failure_penalty_under_worst_case": round(mm.expected_failure_penalty, 4),
        "total": round(mm.total_payoff, 4),
    }


def _game_analysis_section(
    chosen: Tuple[int, ...],
    equipment: List[EquipmentRisk],
    config: Module4Config,
    actions: Tuple[MaintenanceAction, ...],
) -> Dict[str, Any]:
    """Pure and mixed Nash summaries for a 2x2 operator vs environment game."""
    defer_vec = _defer_only_assignment(len(equipment), config)
    _, fp_d_base, obj_defer_base = evaluate_objective(
        defer_vec, equipment, actions, config.failure_cost_scale
    )
    _, fp_o_base, obj_opt_base = evaluate_objective(
        chosen, equipment, actions, config.failure_cost_scale
    )
    eq_stress = _scale_risks(equipment, STRESS_RISK_FACTOR)
    _, fp_d_stress, obj_defer_stress = evaluate_objective(
        defer_vec, eq_stress, actions, config.failure_cost_scale
    )
    _, fp_o_stress, obj_opt_stress = evaluate_objective(
        chosen, eq_stress, actions, config.failure_cost_scale
    )

    payoff_row = (
        (-round(obj_opt_base, 4), -round(obj_opt_stress, 4)),
        (-round(obj_defer_base, 4), -round(obj_defer_stress, 4)),
    )
    payoff_col = (
        (round(fp_o_base, 4), round(fp_o_stress, 4)),
        (round(fp_d_base, 4), round(fp_d_stress, 4)),
    )
    nash_pure = pure_nash_equilibria_2x2(payoff_row, payoff_col)

    a, b = payoff_row[0]
    c, d = payoff_row[1]
    mixed_zs = mixed_nash_zero_sum_2x2(a, b, c, d)

    return {
        "description": (
            "2x2 scan: row = optimized schedule vs all-defer; "
            f"col = baseline risk vs stressed risks (factor {STRESS_RISK_FACTOR}). "
            "Row utility is negative total objective (minimize cost); "
            "column utility is failure penalty. "
            "mixed_nash_zero_sum uses the row payoff matrix only, zero-sum (column minimizes row)."
        ),
        "payoff_row_operator_utility": [list(payoff_row[0]), list(payoff_row[1])],
        "payoff_col_environment_utility": [list(payoff_col[0]), list(payoff_col[1])],
        "pure_nash_equilibria": nash_pure,
        "mixed_nash_zero_sum_row_matrix": {
            "matrix": [list(payoff_row[0]), list(payoff_row[1])],
            "equilibrium": mixed_zs,
        },
    }


def optimize_maintenance_plan(
    diagnosis_path: str | Path,
    config_path: str | Path,
    *,
    production_schedule_path: str | Path | None = None,
) -> Dict[str, Any]:
    """
    Build a maintenance plan from Module 3 diagnosis JSON and Module 4 config.

    Args:
        diagnosis_path: Path to ``diagnosis.json`` (Module 3 output).
        config_path: Path to Module 4 maintenance config JSON.
        production_schedule_path: Optional JSON that may tighten ``max_total_downtime_hours``.

    Returns:
        Dict ready for JSON serialization (``maintenance_plan.json`` shape).
    """
    base_config = load_module4_config(config_path)
    schedule = (
        load_production_schedule(production_schedule_path)
        if production_schedule_path
        else None
    )
    config, prod_meta = apply_production_downtime_cap(base_config, schedule)

    equipment = load_equipment_risks(diagnosis_path)
    if not equipment:
        return {
            "assignments": [],
            "totals": {"maintenance_cost": 0.0, "failure_penalty": 0.0, "objective": 0.0},
            "optimization": {},
            "tradeoffs": [],
            "game_analysis": {},
            "contingency": {},
            "meta": {
                "note": "no equipment in diagnosis.json",
                "production_schedule": prod_meta,
            },
        }

    actions = config.actions
    eq_list = list(equipment)
    chosen, chosen_obj, method, hc_obj, hc_meta, sa_it, sa_obj = _run_hill_climb_and_anneal(
        eq_list, config
    )

    mc, fp, obj = evaluate_objective(chosen, equipment, actions, config.failure_cost_scale)
    if abs(obj - chosen_obj) >= OBJECTIVE_MATCH_EPS:
        raise RuntimeError(
            "Module 4 objective mismatch between optimizer selection and final evaluation"
        )

    tradeoffs = _budget_tradeoffs(eq_list, config)
    contingency = {"single_full_repair_minimax": _contingency_minimax_block(eq_list, config)}
    game_analysis = _game_analysis_section(chosen, eq_list, config, actions)

    return {
        "assignments": _assignment_to_rows(chosen, eq_list, actions),
        "totals": {
            "maintenance_cost": round(mc, 4),
            "failure_penalty": round(fp, 4),
            "objective": round(obj, 4),
        },
        "meta": {
            "production_schedule": prod_meta,
            "effective_max_total_downtime_hours": config.max_total_downtime_hours,
        },
        "optimization": {
            "recommended_method": method,
            "hill_climbing": {"objective": round(hc_obj, 4), **hc_meta},
            "simulated_annealing": {"objective": round(sa_obj, 4), "iterations": sa_it},
        },
        "tradeoffs": tradeoffs,
        "contingency": contingency,
        "game_analysis": game_analysis,
    }


def run_module4(
    diagnosis_path: str | Path,
    config_path: str | Path,
    output_dir: str | Path,
    *,
    production_schedule_path: str | Path | None = None,
) -> None:
    """
    Write ``maintenance_plan.json`` under ``output_dir``.

    Args:
        diagnosis_path: Module 3 ``diagnosis.json``.
        config_path: Module 4 maintenance config JSON.
        output_dir: Directory to create or reuse for output.
        production_schedule_path: Optional production downtime cap JSON.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plan = optimize_maintenance_plan(
        diagnosis_path,
        config_path,
        production_schedule_path=production_schedule_path,
    )
    out = output_dir / "maintenance_plan.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    print(f"Module 4 wrote {out} ({len(plan.get('assignments', []))} assignments).")
