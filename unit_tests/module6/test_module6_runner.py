"""
Module 6 runner integration-style test: full ``run_module6`` with temp config
pointing at repo ``mdp.json``; asserts all three output JSON files and policy shape.
"""

from __future__ import annotations

import json
from pathlib import Path

from equipment_monitoring.module6.runner import run_module6


def _repo_src_data() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "data" / "module6"


def test_run_module6_writes_outputs(tmp_path: Path) -> None:
    diag = {
        "equipment": [
            {"equipment_id": "E1", "diagnoses": [{"hypothesis": "x", "score": 0.9}]},
        ]
    }
    diag_path = tmp_path / "diagnosis.json"
    diag_path.write_text(json.dumps(diag), encoding="utf-8")

    mdp_path = _repo_src_data() / "mdp.json"
    cfg = {
        "gamma": 0.9,
        "alpha": 0.2,
        "epsilon_start": 0.1,
        "epsilon_end": 0.05,
        "epsilon_decay_episodes": 5,
        "num_episodes": 30,
        "max_steps_per_episode": 5,
        "random_seed": 3,
        "risk_thresholds": [0.33, 0.66],
        "mdp_path": str(mdp_path),
    }
    cfg_path = tmp_path / "module6_config.json"
    cfg_path.write_text(json.dumps(cfg), encoding="utf-8")

    out = tmp_path / "out"
    run_module6(
        diagnosis_path=diag_path,
        module6_config_path=cfg_path,
        output_dir=out,
    )

    assert (out / "rl_policy.json").is_file()
    assert (out / "rl_training.json").is_file()
    assert (out / "rl_metrics.json").is_file()
    pol = json.loads((out / "rl_policy.json").read_text(encoding="utf-8"))
    assert "policy" in pol and "risk_high" in pol["policy"]
    assert pol["policy"]["risk_high"] in ("defer", "inspect", "repair")
