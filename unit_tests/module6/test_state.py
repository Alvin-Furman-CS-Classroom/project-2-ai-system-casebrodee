"""Tests for diagnosis → risk bucket mapping and Module 6–scoped diagnosis errors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from equipment_monitoring.module6.loader import Module6ConfigError
from equipment_monitoring.module6.state import (
    equipment_mdp_start_states,
    equipment_risk_buckets,
    mdp_supports_m1hot_rich_states,
    risk_scalar_to_bucket,
)


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


def test_mdp_supports_m1hot_rich_states() -> None:
    assert mdp_supports_m1hot_rich_states(["risk_low", "risk_mid", "risk_high"]) is False
    assert mdp_supports_m1hot_rich_states(["risk_mid", "risk_mid_m1hot"]) is True


def test_equipment_mdp_start_states_plain_three_state_mdp(tmp_path: Path) -> None:
    diag = {
        "equipment": [
            {"equipment_id": "A", "diagnoses": [{"hypothesis": "h", "score": 0.5}]},
        ]
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(diag), encoding="utf-8")
    mdp_states = ["risk_low", "risk_mid", "risk_high"]
    got = equipment_mdp_start_states(
        p,
        (0.33, 0.66),
        mdp_states,
        classifications_path=None,
        m1_anomaly_rate_alert=0.35,
        m1_confidence_alert_fallback=0.55,
    )
    assert got == ["risk_mid"]


def test_equipment_mdp_start_states_m1hot_from_meta(tmp_path: Path) -> None:
    diag = {
        "equipment": [
            {
                "equipment_id": "A",
                "diagnoses": [{"hypothesis": "h", "score": 0.5}],
                "meta": {"m1_max_confidence": 0.9},
            },
        ]
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(diag), encoding="utf-8")
    mdp_states = [
        "risk_low",
        "risk_low_m1hot",
        "risk_mid",
        "risk_mid_m1hot",
        "risk_high",
        "risk_high_m1hot",
    ]
    got = equipment_mdp_start_states(
        p,
        (0.33, 0.66),
        mdp_states,
        classifications_path=None,
        m1_anomaly_rate_alert=0.35,
        m1_confidence_alert_fallback=0.55,
    )
    assert got == ["risk_mid_m1hot"]


def test_equipment_mdp_start_states_m1hot_from_classifications(tmp_path: Path) -> None:
    diag = {
        "equipment": [
            {"equipment_id": "A", "diagnoses": [{"hypothesis": "h", "score": 0.5}], "meta": {}},
        ]
    }
    p = tmp_path / "d.json"
    p.write_text(json.dumps(diag), encoding="utf-8")
    cls = tmp_path / "c.jsonl"
    cls.write_text(
        '{"equipment_id":"A","status":"anomaly"}\n'
        '{"equipment_id":"A","status":"anomaly"}\n'
        '{"equipment_id":"A","status":"normal"}\n',
        encoding="utf-8",
    )
    mdp_states = ["risk_mid", "risk_mid_m1hot"]
    got = equipment_mdp_start_states(
        p,
        (0.33, 0.66),
        mdp_states,
        classifications_path=cls,
        m1_anomaly_rate_alert=0.35,
        m1_confidence_alert_fallback=0.55,
    )
    assert got == ["risk_mid_m1hot"]
