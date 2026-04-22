"""
Tests for Module 6 Q-learning: epsilon schedule, Bellman backup, training convergence
on a one-state toy MDP, and deterministic transition sampling.
"""

from __future__ import annotations

import random
from pathlib import Path

from equipment_monitoring.module6.loader import JsonMDP, Module6Config, TransitionOutcome
from equipment_monitoring.module6.mdp import sample_step
from equipment_monitoring.module6.q_learning import (
    epsilon_at_episode,
    q_learning_update,
    train_q_learning,
)


def _one_state_mdp() -> JsonMDP:
    s = ("risk_low",)
    a = ("defer",)
    t = {
        "risk_low": {
            "defer": (TransitionOutcome(1.0, "risk_low", -1.0),),
        }
    }
    return JsonMDP(states=s, actions=a, transitions=t, initial_state_weights={"risk_low": 1.0})


def test_epsilon_linear_decay() -> None:
    cfg = Module6Config(
        gamma=0.9,
        alpha=0.1,
        epsilon_start=0.3,
        epsilon_end=0.1,
        epsilon_decay_episodes=10,
        num_episodes=100,
        max_steps_per_episode=5,
        random_seed=0,
        risk_thresholds=(0.33, 0.66),
        mdp_path=Path("x"),
        module4_config_path=None,
        classifications_path=None,
        m1_anomaly_rate_alert=0.35,
        m1_confidence_alert_fallback=0.55,
    )
    assert abs(epsilon_at_episode(0, cfg) - 0.3) < 1e-9
    assert abs(epsilon_at_episode(5, cfg) - 0.2) < 1e-9
    assert abs(epsilon_at_episode(10, cfg) - 0.1) < 1e-9
    assert epsilon_at_episode(999, cfg) == 0.1


def test_q_learning_update_manual() -> None:
    mdp = _one_state_mdp()
    q: dict = {}
    q_learning_update(q, "risk_low", "defer", -1.0, "risk_low", mdp, gamma=0.9, alpha=0.5)
    # old 0, target = -1 + 0.9*0 = -1, new = 0 + 0.5*(-1-0) = -0.5
    assert abs(q[("risk_low", "defer")] + 0.5) < 1e-9


def test_sample_step_deterministic() -> None:
    mdp = _one_state_mdp()
    rng = random.Random(0)
    s2, r = sample_step(rng, mdp, "risk_low", "defer")
    assert s2 == "risk_low" and r == -1.0


def test_train_reduces_cost_on_toy_mdp() -> None:
    """One-state MDP: defer always -1; with enough episodes Q(defer) should approach -1/(1-gamma) for greedy."""
    mdp = _one_state_mdp()
    cfg = Module6Config(
        gamma=0.9,
        alpha=0.25,
        epsilon_start=0.0,
        epsilon_end=0.0,
        epsilon_decay_episodes=0,
        num_episodes=500,
        max_steps_per_episode=1,
        random_seed=7,
        risk_thresholds=(0.33, 0.66),
        mdp_path=Path("x"),
        module4_config_path=None,
        classifications_path=None,
        m1_anomaly_rate_alert=0.35,
        m1_confidence_alert_fallback=0.55,
    )
    rng = random.Random(cfg.random_seed)
    q, _hist = train_q_learning(mdp, cfg, ["risk_low"], rng)
    q_defer = q.get(("risk_low", "defer"), 0.0)
    # steady-state Q ~ -1 / (1-0.9) = -10
    assert q_defer < -8.0
