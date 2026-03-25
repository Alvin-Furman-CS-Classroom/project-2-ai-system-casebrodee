"""Tests for Module 4 game-theory helpers."""

import pytest

from equipment_monitoring.module4.game_theory import (
    minimax_single_full_repair,
    mixed_nash_zero_sum_2x2,
    pure_nash_equilibria_2x2,
)


def test_minimax_single_full_repair_picks_high_risk() -> None:
    mm = minimax_single_full_repair(
        ["M1", "M2"],
        [0.9, 0.2],
        repair_action_cost=100.0,
        post_repair_risk_multiplier=0.1,
        failure_cost_scale=1000.0,
    )
    assert mm.chosen_equipment == "M1"


def test_mixed_nash_zero_sum_interior() -> None:
    r = mixed_nash_zero_sum_2x2(1.0, -1.0, -1.0, 1.0)
    assert r["degenerate"] is False
    assert r["row_probability_strategy_0"] == pytest.approx(0.5)
    assert r["col_probability_strategy_0"] == pytest.approx(0.5)
    assert r["value_to_row"] == pytest.approx(0.0)


def test_pure_nash_coordination_game() -> None:
    pr = ((3, 0), (0, 2))
    pc = ((2, 0), (0, 3))
    eq = pure_nash_equilibria_2x2(pr, pc)
    assert len(eq) == 2
    cells = {(e["row_strategy_index"], e["col_strategy_index"]) for e in eq}
    assert cells == {(0, 0), (1, 1)}
