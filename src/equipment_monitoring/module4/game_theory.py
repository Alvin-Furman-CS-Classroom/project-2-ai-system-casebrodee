"""Small game-theory helpers: minimax for one repair vs nature, pure Nash for 2x2 bimatrix."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class MinimaxRepairResult:
    """Maintainer chooses one equipment to apply a full repair; nature picks failure target."""

    chosen_equipment: str
    worst_case_target: str
    maintainer_cost: float
    expected_failure_penalty: float
    total_payoff: float


def minimax_single_full_repair(
    equipment_ids: Sequence[str],
    risks: Sequence[float],
    repair_action_cost: float,
    post_repair_risk_multiplier: float,
    failure_cost_scale: float,
) -> MinimaxRepairResult:
    """
    Maintainer picks exactly one machine k to receive repair (cost + scaled residual risk).
    Nature then picks machine j to maximize maintainer's failure penalty.

    Residual risk after repairing k: risk_i * mult if i==k else risk_i (unchanged).
    Failure penalty at leaf: failure_cost_scale * risk'_j (single worst machine).
    """
    if len(equipment_ids) != len(risks) or not equipment_ids:
        raise ValueError("equipment_ids and risks must be same non-empty length")

    best_val = float("inf")
    best_k = equipment_ids[0]
    worst_j_for_best = equipment_ids[0]

    for k_idx, k_id in enumerate(equipment_ids):
        cost = repair_action_cost
        worst_penalty = 0.0
        worst_j = equipment_ids[0]
        for j_idx, j_id in enumerate(equipment_ids):
            r = risks[j_idx]
            if j_idx == k_idx:
                r = r * post_repair_risk_multiplier
            pen = failure_cost_scale * r
            if pen > worst_penalty + 1e-15:
                worst_penalty = pen
                worst_j = j_id
        total = cost + worst_penalty
        if total < best_val - 1e-12:
            best_val = total
            best_k = k_id
            worst_j_for_best = worst_j

    r_after = list(risks)
    k_idx = list(equipment_ids).index(best_k)
    r_after[k_idx] = r_after[k_idx] * post_repair_risk_multiplier
    worst_idx = max(range(len(r_after)), key=lambda i: r_after[i])
    return MinimaxRepairResult(
        chosen_equipment=best_k,
        worst_case_target=worst_j_for_best,
        maintainer_cost=repair_action_cost,
        expected_failure_penalty=failure_cost_scale * r_after[worst_idx],
        total_payoff=best_val,
    )


def pure_nash_equilibria_2x2(
    payoff_row: Tuple[Tuple[float, float], Tuple[float, float]],
    payoff_col: Tuple[Tuple[float, float], Tuple[float, float]],
) -> List[Dict[str, Any]]:
    """
    Find all pure-strategy Nash equilibria for a 2x2 game.
    payoff_row[i][j] is row player utility; payoff_col[i][j] is column player utility.
    """
    equilibria: List[Dict[str, Any]] = []
    for i in range(2):
        for j in range(2):
            u_r = payoff_row[i][j]
            u_c = payoff_col[i][j]
            row_dev0 = payoff_row[1 - i][j]
            col_dev0 = payoff_col[i][1 - j]
            row_best = u_r >= row_dev0 - 1e-12
            col_best = u_c >= col_dev0 - 1e-12
            if row_best and col_best:
                equilibria.append(
                    {
                        "row_strategy_index": i,
                        "col_strategy_index": j,
                        "payoff_row": u_r,
                        "payoff_col": u_c,
                    }
                )
    return equilibria


def mixed_nash_zero_sum_2x2(a: float, b: float, c: float, d: float) -> Dict[str, Any]:
    """
    Mixed-strategy Nash equilibrium for a 2×2 **zero-sum** game (row maximizes, column minimizes).

    Payoff matrix (row's utility):

            col0    col1
    row0      a       b
    row1      c       d

    Uses the standard closed form: p = (d-c)/D, q = (d-b)/D, value = (ad-bc)/D
    with D = a - b - c + d. If D is near zero, the game is degenerate (pure strategies often suffice).
    """
    delta = a - b - c + d
    if abs(delta) < 1e-12:
        return {
            "degenerate": True,
            "reason": "payoff_differences_singular",
            "note": "Use pure_nash_equilibria_2x2 on a general-sum game or check for dominance.",
        }
    p = (d - c) / delta
    q = (d - b) / delta
    value = (a * d - b * c) / delta
    return {
        "degenerate": False,
        "row_probability_strategy_0": round(max(0.0, min(1.0, p)), 6),
        "col_probability_strategy_0": round(max(0.0, min(1.0, q)), 6),
        "value_to_row": round(value, 6),
        "delta_denominator": round(delta, 6),
    }
