"""
Tests for Module 6 MDP and config loading.

Covers probability-sum validation, unknown next states, and path resolution
for ``module6_config.json`` relative to ``mdp.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from equipment_monitoring.module6.loader import (
    Module6ConfigError,
    load_mdp_json,
    load_module6_config,
)


def test_load_mdp_rejects_bad_probability_sum(tmp_path: Path) -> None:
    bad = {
        "states": ["a", "b"],
        "actions": ["x"],
        "transitions": {"a": {"x": [[0.5, "b", 0.0]]}},  # sums to 0.5
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(Module6ConfigError, match="sum"):
        load_mdp_json(p)


def test_load_mdp_rejects_unknown_next_state(tmp_path: Path) -> None:
    bad = {
        "states": ["a", "b"],
        "actions": ["x"],
        "transitions": {"a": {"x": [[1.0, "c", 0.0]]}},
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(Module6ConfigError, match="unknown next_state"):
        load_mdp_json(p)


def test_load_module6_config_resolves_mdp_path(tmp_path: Path) -> None:
    mdp = {
        "states": ["s0"],
        "actions": ["a0"],
        "initial_state_weights": {"s0": 1.0},
        "transitions": {"s0": {"a0": [[1.0, "s0", -1.0]]}},
    }
    (tmp_path / "mdp.json").write_text(json.dumps(mdp), encoding="utf-8")
    cfg = {
        "gamma": 0.9,
        "alpha": 0.1,
        "epsilon_start": 0.2,
        "epsilon_end": 0.1,
        "epsilon_decay_episodes": 10,
        "num_episodes": 5,
        "max_steps_per_episode": 3,
        "random_seed": 1,
        "risk_thresholds": [0.4, 0.7],
        "mdp_path": "mdp.json",
    }
    cp = tmp_path / "c.json"
    cp.write_text(json.dumps(cfg), encoding="utf-8")
    loaded = load_module6_config(cp)
    assert loaded.mdp_path == (tmp_path / "mdp.json").resolve()
