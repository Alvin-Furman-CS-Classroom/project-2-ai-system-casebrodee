"""
Module 6 integration smoke: ``outputs/full_pipeline/module3/diagnosis.json`` (if present)
plus bundled ``src/data/module6`` MDP; fast training config in a temp file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from equipment_monitoring.module6.runner import run_module6


@pytest.fixture
def full_pipeline_diagnosis() -> Path:
    root = Path(__file__).resolve().parents[2]
    p = root / "outputs" / "full_pipeline" / "module3" / "diagnosis.json"
    if not p.is_file():
        pytest.skip("full_pipeline diagnosis fixture not present")
    return p


def test_module6_on_full_pipeline_diagnosis(tmp_path: Path, full_pipeline_diagnosis: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    m6_dir = root / "src" / "data" / "module6"
    cfg_path = m6_dir / "module6_config.json"
    fast_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    fast_cfg["num_episodes"] = 80
    fast_cfg["max_steps_per_episode"] = 6
    fast_cfg["mdp_path"] = str(m6_dir / "mdp.json")
    fast_cfg["module4_config_path"] = str(root / "src" / "data" / "module4" / "module4_config.json")
    custom = tmp_path / "fast_module6.json"
    custom.write_text(json.dumps(fast_cfg), encoding="utf-8")

    out = tmp_path / "module6_out"
    run_module6(
        diagnosis_path=full_pipeline_diagnosis,
        module6_config_path=custom,
        output_dir=out,
    )
    metrics = json.loads((out / "rl_metrics.json").read_text(encoding="utf-8"))
    assert "baseline_always_defer" in metrics
    assert metrics["mdp"]["num_states"] == 6
