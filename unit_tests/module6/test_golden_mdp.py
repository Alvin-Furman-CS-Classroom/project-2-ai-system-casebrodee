"""
Golden MDP: known optimal greedy actions after Q-learning (regression guard).

The fixture ``golden_policy_mdp.json`` is a two-state self-loop MDP:
  - g_low:  inspect is strictly best (least negative immediate reward).
  - g_high: repair is strictly best.

Training uses gamma=0 and max_steps_per_episode=1 so Q(s,a) targets equal the
immediate reward; with enough episodes the greedy policy matches the optimum.
"""

from __future__ import annotations

import random
from pathlib import Path

from equipment_monitoring.module6.loader import Module6Config, load_mdp_json
from equipment_monitoring.module6.q_learning import greedy_policy_from_q, train_q_learning


def _fixture_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "src"
        / "data"
        / "module6"
        / "fixtures"
        / "golden_policy_mdp.json"
    )


def test_golden_mdp_greedy_policy_matches_optimum() -> None:
    mdp = load_mdp_json(_fixture_path())
    cfg = Module6Config(
        gamma=0.0,
        alpha=0.35,
        epsilon_start=0.45,
        epsilon_end=0.0,
        epsilon_decay_episodes=3500,
        num_episodes=9000,
        max_steps_per_episode=1,
        random_seed=2026,
        risk_thresholds=(0.33, 0.66),
        mdp_path=Path("unused.json"),
        module4_config_path=None,
        classifications_path=None,
        m1_anomaly_rate_alert=0.35,
        m1_confidence_alert_fallback=0.55,
    )
    rng = random.Random(cfg.random_seed)
    buckets = ["g_low", "g_high"]
    q, _hist = train_q_learning(mdp, cfg, buckets, rng)
    policy_rng = random.Random(0)
    policy = greedy_policy_from_q(q, mdp, policy_rng)

    assert policy["g_low"] == "inspect", f"expected inspect at g_low, got {policy['g_low']!r}, Q={dict(q)}"
    assert policy["g_high"] == "repair", f"expected repair at g_high, got {policy['g_high']!r}, Q={dict(q)}"
