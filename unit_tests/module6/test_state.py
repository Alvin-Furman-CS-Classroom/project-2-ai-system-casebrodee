"""Tests for diagnosis → risk bucket mapping and Module 6–scoped diagnosis errors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from equipment_monitoring.module6.loader import Module6ConfigError
from equipment_monitoring.module6.state import equipment_risk_buckets, risk_scalar_to_bucket


def test_risk_scalar_to_bucket_boundaries() -> None:
    th = (0.33, 0.66)
    assert risk_scalar_to_bucket(0.0, th) == "risk_low"
    assert risk_scalar_to_bucket(0.32, th) == "risk_low"
    assert risk_scalar_to_bucket(0.33, th) == "risk_mid"
    assert risk_scalar_to_bucket(0.65, th) == "risk_mid"
    assert risk_scalar_to_bucket(0.66, th) == "risk_high"
    assert risk_scalar_to_bucket(1.0, th) == "risk_high"


def test_equipment_risk_buckets_from_diagnosis(tmp_path: Path) -> None:
    diag = {
        "equipment": [
            {
                "equipment_id": "A",
                "diagnoses": [{"hypothesis": "h", "score": 0.2}],
            },
            {
                "equipment_id": "B",
                "diagnoses": [{"hypothesis": "h2", "score": 0.77}],
            },
        ]
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(diag), encoding="utf-8")
    buckets = equipment_risk_buckets(p, (0.33, 0.66))
    assert buckets == ["risk_low", "risk_high"]


def test_equipment_risk_buckets_invalid_diagnosis_raises_module6(tmp_path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(Module6ConfigError, match="Invalid diagnosis.json for Module 6"):
        equipment_risk_buckets(p, (0.33, 0.66))


def test_equipment_risk_buckets_missing_equipment_array_raises_module6(tmp_path) -> None:
    p = tmp_path / "d.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(Module6ConfigError, match="Invalid diagnosis.json for Module 6"):
        equipment_risk_buckets(p, (0.33, 0.66))
