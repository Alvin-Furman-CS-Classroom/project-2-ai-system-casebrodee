"""Unit tests for Module 3 fact building from M1/M2 artifacts (`facts` module)."""

import json
from pathlib import Path

import pytest

from equipment_monitoring.module3.facts import build_facts_per_equipment


def _write_artifacts(
    tmp_path: Path,
    *,
    classifications_lines: list[str],
    sequences: list | None = None,
    warning_signs: list | None = None,
) -> tuple[Path, Path, Path]:
    cls_path = tmp_path / "classifications.jsonl"
    cls_path.write_text("\n".join(classifications_lines) + "\n", encoding="utf-8")
    seq_path = tmp_path / "sequences.json"
    seq_path.write_text(
        json.dumps({"sequences": sequences or []}),
        encoding="utf-8",
    )
    warn_path = tmp_path / "warning_signs.json"
    warn_path.write_text(
        json.dumps({"warning_signs": warning_signs or []}),
        encoding="utf-8",
    )
    return cls_path, seq_path, warn_path


def test_build_facts_normal_equipment_no_m2_path(tmp_path: Path) -> None:
    """Normal M1 readings; equipment not on any failure sequence."""
    cls, seq, warn = _write_artifacts(
        tmp_path,
        classifications_lines=[
            json.dumps(
                {
                    "equipment_id": "pump_A",
                    "status": "normal",
                    "confidence": 0.95,
                    "violated_rules": [],
                }
            )
        ],
        sequences=[{"frequency": 3, "machines": ["other_pump"]}],
        warning_signs=[{"predictive_score": 0.8}],
    )
    per_eq, meta = build_facts_per_equipment(cls, seq, warn)

    assert "pump_A" in per_eq
    facts = per_eq["pump_A"]
    assert ("status", "pump_A", "normal") in facts
    assert ("m2_sequence_freq", "pump_A", "0") in facts
    assert ("m2_top_predictive", "pump_A", "0") in facts
    assert ("m2_on_failure_path", "pump_A") not in facts
    assert meta["pump_A"]["m2_on_failure_path"] is False
    assert meta["pump_A"]["m1_max_confidence"] == 0.95


def test_build_facts_anomaly_violations_and_m2_path(tmp_path: Path) -> None:
    """Anomaly with violations; equipment appears in failure sequences."""
    cls, seq, warn = _write_artifacts(
        tmp_path,
        classifications_lines=[
            json.dumps(
                {
                    "equipment_id": "M1",
                    "status": "anomaly",
                    "confidence": 0.82,
                    "violated_rules": ["temperature_high", "pressure_low"],
                }
            )
        ],
        sequences=[{"frequency": 5, "machines": ["M1", "M2"]}],
        warning_signs=[{"predictive_score": 0.65}, {"predictive_score": 0.4}],
    )
    per_eq, meta = build_facts_per_equipment(cls, seq, warn)

    facts = per_eq["M1"]
    assert ("status", "M1", "anomaly") in facts
    assert ("violated", "M1", "temperature_high") in facts
    assert ("violated", "M1", "pressure_low") in facts
    assert ("m2_on_failure_path", "M1") in facts
    assert ("m2_sequence_freq", "M1", "5") in facts
    assert ("m2_top_predictive", "M1", "0.65") in facts
    assert meta["M1"]["m2_top_predictive"] == 0.65
    assert meta["M1"]["violated_rules"] == ["pressure_low", "temperature_high"]


def test_build_facts_multiple_rows_same_equipment(tmp_path: Path) -> None:
    """Max confidence and union of violations across rows."""
    cls, seq, warn = _write_artifacts(
        tmp_path,
        classifications_lines=[
            json.dumps(
                {
                    "equipment_id": "E1",
                    "status": "normal",
                    "confidence": 0.5,
                    "violated_rules": [],
                }
            ),
            json.dumps(
                {
                    "equipment_id": "E1",
                    "status": "anomaly",
                    "confidence": 0.9,
                    "violated_rules": ["vibration_high"],
                }
            ),
        ],
    )
    per_eq, meta = build_facts_per_equipment(cls, seq, warn)
    assert meta["E1"]["m1_max_confidence"] == 0.9
    assert ("status", "E1", "anomaly") in per_eq["E1"]
    assert ("violated", "E1", "vibration_high") in per_eq["E1"]


def test_build_facts_skips_row_without_equipment_id(tmp_path: Path) -> None:
    cls, seq, warn = _write_artifacts(
        tmp_path,
        classifications_lines=[
            json.dumps({"status": "normal", "confidence": 1.0}),
            json.dumps(
                {
                    "equipment_id": "only_me",
                    "status": "normal",
                    "confidence": 0.7,
                    "violated_rules": [],
                }
            ),
        ],
    )
    per_eq, _ = build_facts_per_equipment(cls, seq, warn)
    assert list(per_eq.keys()) == ["only_me"]


def test_build_facts_empty_classifications(tmp_path: Path) -> None:
    cls, seq, warn = _write_artifacts(tmp_path, classifications_lines=[])
    per_eq, meta = build_facts_per_equipment(cls, seq, warn)
    assert per_eq == {}
    assert meta == {}
