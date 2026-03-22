"""Unit tests for Module 3 diagnosis scoring and explanation trees (`diagnosis` module)."""

import pytest

from equipment_monitoring.module3.diagnosis import (
    _explain_step,
    _score_hypothesis,
    build_diagnosis_record,
)
from equipment_monitoring.module3.logic import Atom, Rule, atom_from_list


def test_score_hypothesis_in_zero_one_range() -> None:
    s = _score_hypothesis(rule_priority=100, m1_confidence=1.0, m2_predictive=1.0)
    assert 0.0 <= s <= 1.0
    assert s == 1.0

    s_low = _score_hypothesis(rule_priority=0, m1_confidence=0.0, m2_predictive=0.0)
    assert s_low == 0.0

    s_mid = _score_hypothesis(rule_priority=50, m1_confidence=0.5, m2_predictive=0.5)
    assert 0.0 < s_mid < 1.0


def test_score_hypothesis_clamps_priority() -> None:
    """Priority outside 0..100 is clamped for scoring."""
    s = _score_hypothesis(rule_priority=200, m1_confidence=0.0, m2_predictive=0.0)
    assert s == pytest.approx(0.45, rel=0.01)


def test_explain_step_primitive_vs_inference() -> None:
    prim: set[Atom] = {("a", "E1")}
    prov: dict = {}
    out = _explain_step(("a", "E1"), prov, prim)
    assert out["kind"] == "fact"
    assert out["atom"] == ["a", "E1"]

    prov2 = {
        ("b", "E1"): ("rule_b", (("a", "E1"),)),
    }
    out2 = _explain_step(("b", "E1"), prov2, prim)
    assert out2["kind"] == "inference"
    assert out2["rule_id"] == "rule_b"
    assert out2["antecedents"][0]["kind"] == "fact"


def test_build_diagnosis_record_with_suggests() -> None:
    equipment_id = "pump_1"
    suggests_atom: Atom = ("suggests", equipment_id, "bearing_wear")
    primitive: set[Atom] = {
        ("status", equipment_id, "anomaly"),
        ("violated", equipment_id, "vibration_high"),
    }
    closed = set(primitive) | {suggests_atom}
    provenance: dict[Atom, tuple[str, tuple[Atom, ...]]] = {
        suggests_atom: (
            "r_bearing",
            (
                ("status", equipment_id, "anomaly"),
                ("violated", equipment_id, "vibration_high"),
            ),
        ),
    }
    rules_index = {
        "r_bearing": Rule(
            id="r_bearing",
            priority=80,
            antecedents=(atom_from_list(["status", "?e", "anomaly"]),),
            consequent=suggests_atom,
            inspection="Inspect bearings.",
        )
    }

    record = build_diagnosis_record(
        equipment_id=equipment_id,
        closed_facts=closed,
        provenance=provenance,
        primitive_facts=primitive,
        rules_index=rules_index,
        m1_max_confidence=0.9,
        m2_top_predictive=0.5,
    )

    assert record["equipment_id"] == equipment_id
    assert len(record["diagnoses"]) == 1
    d0 = record["diagnoses"][0]
    assert d0["hypothesis"] == "bearing_wear"
    assert d0["supporting_rule_ids"] == ["r_bearing"]
    assert d0["inspection"] == "Inspect bearings."
    assert d0["explanation"]["kind"] == "inference"
    assert "primitive_facts" in record
    assert any("status" in f for f in record["primitive_facts"])


def test_build_diagnosis_record_no_suggests() -> None:
    primitive: set[Atom] = {("status", "E", "normal")}
    record = build_diagnosis_record(
        equipment_id="E",
        closed_facts=set(primitive),
        provenance={},
        primitive_facts=primitive,
        rules_index={},
        m1_max_confidence=1.0,
        m2_top_predictive=0.0,
    )
    assert record["diagnoses"] == []
