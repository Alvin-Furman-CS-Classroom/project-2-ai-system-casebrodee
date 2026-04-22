"""Unit tests for Module 3 runner (`infer_batch` / `run_module3`)."""

import json
from pathlib import Path

import pytest

from equipment_monitoring.module3 import runner


def test_infer_batch_writes_expected_shape(tmp_path: Path) -> None:
    """infer_batch produces diagnosis.json-shaped dict from synthetic artifacts."""
    kb_path = tmp_path / "kb.json"
    kb_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "simple",
                        "priority": 90,
                        "antecedents": [["status", "?e", "anomaly"]],
                        "consequent": ["suggests", "?e", "check_equipment"],
                        "inspection": "Visual inspection.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cls = tmp_path / "classifications.jsonl"
    cls.write_text(
        json.dumps(
            {
                "equipment_id": "unit_test_eq",
                "status": "anomaly",
                "confidence": 0.88,
                "violated_rules": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seq = tmp_path / "sequences.json"
    seq.write_text(json.dumps({"sequences": []}), encoding="utf-8")
    warn = tmp_path / "warning_signs.json"
    warn.write_text(json.dumps({"warning_signs": []}), encoding="utf-8")

    result = runner.infer_batch(
        kb_path=kb_path,
        classifications_path=cls,
        sequences_path=seq,
        warning_signs_path=warn,
    )

    assert "equipment" in result
    assert len(result["equipment"]) == 1
    block = result["equipment"][0]
    assert block["equipment_id"] == "unit_test_eq"
    assert "diagnoses" in block
    assert "primitive_facts" in block
    assert "meta" in block
    assert len(block["diagnoses"]) >= 1
    assert block["diagnoses"][0]["hypothesis"] == "check_equipment"


def test_run_module3_creates_diagnosis_json(tmp_path: Path) -> None:
    kb_path = tmp_path / "kb.json"
    kb_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "id": "r",
                        "priority": 10,
                        "antecedents": [["status", "?e", "normal"]],
                        "consequent": ["suggests", "?e", "routine_ok"],
                        "inspection": "OK",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    cls = tmp_path / "classifications.jsonl"
    cls.write_text(
        json.dumps(
            {
                "equipment_id": "X",
                "status": "normal",
                "confidence": 1.0,
                "violated_rules": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    seq = tmp_path / "sequences.json"
    seq.write_text(json.dumps({"sequences": []}), encoding="utf-8")
    warn = tmp_path / "warning_signs.json"
    warn.write_text(json.dumps({"warning_signs": []}), encoding="utf-8")
    out_dir = tmp_path / "out"

    runner.run_module3(
        kb_path=kb_path,
        classifications_path=cls,
        sequences_path=seq,
        warning_signs_path=warn,
        output_dir=out_dir,
    )

    diag = out_dir / "diagnosis.json"
    assert diag.exists()
    data = json.loads(diag.read_text(encoding="utf-8"))
    assert data["equipment"][0]["equipment_id"] == "X"
