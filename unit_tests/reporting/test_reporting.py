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


def test_generate_report_notes_missing_files(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    report_path = outputs / "report.html"

    reporting.generate_report(outputs, report_path)
    html = report_path.read_text(encoding="utf-8")

    assert "Missing file:" in html
    assert "No Module 1 data yet." in html


def test_generate_report_handles_invalid_json(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    (outputs / "module2").mkdir(parents=True, exist_ok=True)
    (outputs / "module2" / "sequences.json").write_text("{bad", encoding="utf-8")

    report_path = outputs / "report.html"
    reporting.generate_report(outputs, report_path)
    html = report_path.read_text(encoding="utf-8")
    assert "Invalid JSON" in html
