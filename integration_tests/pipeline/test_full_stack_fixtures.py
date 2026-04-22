"""
Phase 5: full stack on tiny in-tmp fixtures (no dependency on outputs/full_pipeline).

Runs Module 1→2→3→4→6 with repo-bundled KB/graph/search/MDP configs, fast Module 6
hyperparameters, then generates the static HTML report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from equipment_monitoring import reporting
from equipment_monitoring.module1 import classifier
from equipment_monitoring.module2 import runner as module2_runner
from equipment_monitoring.module3 import runner as module3_runner
from equipment_monitoring.module4 import runner as module4_runner
from equipment_monitoring.module6 import runner as module6_runner


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _tiny_readings_csv() -> str:
    # Same shape as integration_tests/module2/test_module1_module2_integration.py
    return (
        "timestamp,equipment_id,temperature,vibration,pressure,failure_status\n"
        "2026-01-01T00:00:00Z,M1,25,1.0,100,0\n"
        "2026-01-01T00:01:00Z,M1,35,2.0,150,0\n"
        "2026-01-01T00:02:00Z,M1,45,4.0,250,0\n"
        "2026-01-01T00:03:00Z,M1,65,5.5,400,1\n"
        "2026-01-01T00:00:00Z,M2,22,1.5,120,0\n"
        "2026-01-01T00:01:00Z,M2,40,3.0,200,0\n"
        "2026-01-01T00:02:00Z,M2,60,5.0,380,1\n"
    )


def test_full_stack_modules_1_through_6_and_report(tmp_path: Path) -> None:
    root = _repo_root()
    kb_path = root / "src" / "data" / "module3" / "kb.json"
    graph_config_path = root / "src" / "data" / "module2" / "graph_config.json"
    search_params_path = root / "src" / "data" / "module2" / "search_params.json"
    m4_cfg_path = root / "src" / "data" / "module4" / "module4_config.json"
    prod_path = root / "src" / "data" / "module4" / "production_schedule.json"
    m6_dir = root / "src" / "data" / "module6"

    for p in (kb_path, graph_config_path, search_params_path, m4_cfg_path, m6_dir / "mdp.json"):
        if not p.exists():
            pytest.skip(f"required repo data missing: {p}")

    out = tmp_path / "outputs"
    m1_out = out / "module1"
    m2_out = out / "module2"
    m3_out = out / "module3"
    m4_out = out / "module4"
    m6_out = out / "module6"

    cfg_path = tmp_path / "config.json"
    specs_path = tmp_path / "specs.json"
    csv_path = tmp_path / "readings_with_failures.csv"
    cfg_path.write_text(
        json.dumps(
            {
                "temperature": {"min": 20.0, "max": 80.0},
                "vibration": {"max": 5.0},
                "pressure": {"min": 10.0, "max": 50.0},
            }
        ),
        encoding="utf-8",
    )
    specs_path.write_text("{}", encoding="utf-8")
    csv_path.write_text(_tiny_readings_csv(), encoding="utf-8")

    classifier.run_module1(
        config_path=cfg_path,
        specs_path=specs_path,
        csv_path=csv_path,
        output_dir=m1_out,
    )
    assert (m1_out / "classifications.jsonl").is_file()

    module2_runner.run_module2(
        data_path=csv_path,
        graph_config_path=graph_config_path,
        search_params_path=search_params_path,
        output_dir=m2_out,
        data_format="module1",
        classifications_path=m1_out / "classifications.jsonl",
    )
    assert (m2_out / "sequences.json").is_file()
    assert (m2_out / "warning_signs.json").is_file()

    module3_runner.run_module3(
        kb_path=kb_path,
        classifications_path=m1_out / "classifications.jsonl",
        sequences_path=m2_out / "sequences.json",
        warning_signs_path=m2_out / "warning_signs.json",
        output_dir=m3_out,
    )
    diag_path = m3_out / "diagnosis.json"
    assert diag_path.is_file()
    diagnosis = json.loads(diag_path.read_text(encoding="utf-8"))
    assert len(diagnosis.get("equipment", [])) == 2

    module4_runner.run_module4(
        diagnosis_path=diag_path,
        config_path=m4_cfg_path,
        output_dir=m4_out,
        production_schedule_path=prod_path if prod_path.is_file() else None,
    )
    plan_path = m4_out / "maintenance_plan.json"
    assert plan_path.is_file()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert "assignments" in plan and "totals" in plan

    base_m6 = json.loads((m6_dir / "module6_config.json").read_text(encoding="utf-8"))
    fast_m6 = {
        **base_m6,
        "num_episodes": 80,
        "max_steps_per_episode": 6,
        "mdp_path": str((m6_dir / "mdp.json").resolve()),
        "module4_config_path": str(m4_cfg_path.resolve()),
    }
    m6_cfg = tmp_path / "fast_module6.json"
    m6_cfg.write_text(json.dumps(fast_m6), encoding="utf-8")

    module6_runner.run_module6(
        diagnosis_path=diag_path,
        module6_config_path=m6_cfg,
        output_dir=m6_out,
        classifications_path=m1_out / "classifications.jsonl",
    )
    for name in ("rl_policy.json", "rl_training.json", "rl_metrics.json"):
        assert (m6_out / name).is_file(), f"missing {name}"
    pol = json.loads((m6_out / "rl_policy.json").read_text(encoding="utf-8"))
    assert "policy" in pol and len(pol["policy"]) >= 3

    report_path = out / "report.html"
    written = reporting.generate_report(out, report_path)
    assert written == report_path
    html = report_path.read_text(encoding="utf-8")
    assert 'id="module6"' in html
    assert "Learned maintenance policy" in html
    assert "What this state means" in html

    data = reporting.load_module_outputs(out)
    assert not data.get("errors_core"), f"unexpected core load errors: {data.get('errors_core')}"

    summary_path = reporting.write_fleet_summary(out)
    assert summary_path == out / "fleet_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["outputs_root"] == str(out.resolve())
    assert summary["artifacts"]["module6_rl_policy_json"] is True
    assert summary["module6"]["policy_state_count"] >= 3
    assert len(summary["module6"]["policy"]) >= 3
