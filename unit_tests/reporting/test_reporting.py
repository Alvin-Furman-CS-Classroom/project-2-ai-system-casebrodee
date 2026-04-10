"""Unit tests for static HTML report generation."""

from __future__ import annotations

import json
from pathlib import Path

from equipment_monitoring import reporting


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_generate_report_with_partial_data(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "module1").mkdir(parents=True, exist_ok=True)
    (outputs / "module1" / "classifications.jsonl").write_text(
        '{"timestamp":"t1","equipment_id":"M1","status":"anomaly","violated_rules":["pressure_high"],"confidence":0.8}\n',
        encoding="utf-8",
    )
    _write_json(
        outputs / "module2" / "sequences.json",
        {"sequences": [{"sequence": ["A", "B"], "frequency": 2, "avg_time_to_failure": 1.5}]},
    )
    _write_json(
        outputs / "module2" / "warning_signs.json",
        {"warning_signs": [{"pattern": "A->B", "predictive_score": 0.9, "frequency": 2, "false_positive_rate": 0.1}]},
    )
    _write_json(outputs / "module3" / "diagnosis.json", {"equipment": []})

    report_path = outputs / "report.html"
    written = reporting.generate_report(outputs, report_path)

    assert written == report_path
    html = report_path.read_text(encoding="utf-8")
    assert "Industrial Equipment Monitoring Report" in html
    assert "Module 1 - Rule-Based Monitoring" in html
    assert "pressure_high" in html
    assert "A-&gt;B" in html
    # Module 6 appears in overview/blueprint/nav even when rl_policy.json is absent
    assert "Module 6 blueprint" in html
    assert 'href="#module6"' in html
    assert "Module 6 policy rows" in html


def test_generate_report_notes_missing_files(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    report_path = outputs / "report.html"

    reporting.generate_report(outputs, report_path)
    html = report_path.read_text(encoding="utf-8")

    assert "Missing file:" in html
    assert "No Module 1 data yet." in html


def test_generate_report_includes_module6_detail_when_rl_outputs_exist(tmp_path: Path) -> None:
    """When module6/rl_policy.json has a non-empty policy, render #module6 body section."""
    outputs = tmp_path / "outputs"
    (outputs / "module1").mkdir(parents=True, exist_ok=True)
    (outputs / "module1" / "classifications.jsonl").write_text(
        '{"timestamp":"t1","equipment_id":"M1","status":"normal","violated_rules":[],"confidence":0.1}\n',
        encoding="utf-8",
    )
    _write_json(outputs / "module2" / "sequences.json", {"sequences": []})
    _write_json(outputs / "module2" / "warning_signs.json", {"warning_signs": []})
    _write_json(outputs / "module3" / "diagnosis.json", {"equipment": []})
    _write_json(
        outputs / "module6" / "rl_policy.json",
        {
            "policy": {
                "risk_low": "defer",
                "risk_mid": "inspect",
                "risk_high": "repair",
            },
            "q_table": {"risk_low": {"defer": -1.0}},
            "meta": {"random_seed": 42, "module5_required": False},
        },
    )
    _write_json(
        outputs / "module6" / "rl_metrics.json",
        {
            "trained_policy_last_window": {
                "mean_return": -120.5,
                "std_return": 2.0,
                "window_episodes": 50,
            },
            "baseline_always_defer": {"mean_return": -100.0, "std_return": 1.0, "eval_episodes": 200},
            "baseline_random": {"mean_return": -110.0, "std_return": 5.0, "eval_episodes": 200},
            "mdp": {"num_states": 3, "num_actions": 3, "states": [], "actions": []},
        },
    )

    report_path = outputs / "report.html"
    reporting.generate_report(outputs, report_path)
    html = report_path.read_text(encoding="utf-8")

    assert 'id="module6"' in html
    assert "Learned maintenance policy" in html
    assert "risk_low" in html and "defer" in html
    assert "Recent training score" in html
    assert "-120.5" in html
    assert "Fleet risk band" in html


def test_generate_report_handles_invalid_json(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "module2").mkdir(parents=True, exist_ok=True)
    (outputs / "module2" / "sequences.json").write_text("{bad", encoding="utf-8")

    report_path = outputs / "report.html"
    reporting.generate_report(outputs, report_path)
    html = report_path.read_text(encoding="utf-8")
    assert "Invalid JSON" in html
