"""Rank diagnoses and build explanation trees from provenance."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from .logic import Atom, Rule, collect_suggests


def _score_hypothesis(
    rule_priority: int,
    m1_confidence: float,
    m2_predictive: float,
) -> float:
    """Heuristic score in [0, 1] — documented blend of KB priority and Modules 1–2."""
    p = max(0, min(100, rule_priority)) / 100.0
    base = 0.45 * p + 0.30 * m1_confidence + 0.25 * m2_predictive
    return round(min(1.0, max(0.0, base)), 4)


def _explain_step(
    fact: Atom,
    provenance: Dict[Atom, Tuple[str, Tuple[Atom, ...]]],
    primitive: Set[Atom],
) -> Dict[str, Any]:
    if fact in primitive:
        return {"kind": "fact", "atom": list(fact)}
    if fact not in provenance:
        return {"kind": "fact", "atom": list(fact)}
    rule_id, parents = provenance[fact]
    return {
        "kind": "inference",
        "rule_id": rule_id,
        "conclusion": list(fact),
        "antecedents": [_explain_step(tuple(p), provenance, primitive) for p in parents],
    }


def build_diagnosis_record(
    equipment_id: str,
    closed_facts: Set[Atom],
    provenance: Dict[Atom, Tuple[str, Tuple[Atom, ...]]],
    primitive_facts: Set[Atom],
    rules_index: Dict[str, Rule],
    m1_max_confidence: float,
    m2_top_predictive: float,
) -> Dict[str, Any]:
    suggests = collect_suggests(closed_facts)
    # suggests: (suggests, equipment, hypothesis_id)
    diagnoses: List[Dict[str, Any]] = []
    seen_hyp: Set[str] = set()

    for atom in suggests:
        if len(atom) < 3:
            continue
        _, eq, hyp = atom[0], atom[1], atom[2]
        if eq != equipment_id:
            continue
        if hyp in seen_hyp:
            continue
        seen_hyp.add(hyp)

        rule_id = provenance.get(atom, ("", ()))[0]
        rule = rules_index.get(rule_id)
        priority = rule.priority if rule else 0
        inspection = rule.inspection if rule else ""

        score = _score_hypothesis(priority, m1_max_confidence, m2_top_predictive)
        explanation = _explain_step(atom, provenance, primitive_facts)

        diagnoses.append(
            {
                "hypothesis": hyp,
                "score": score,
                "supporting_rule_ids": [rule_id] if rule_id else [],
                "explanation": explanation,
                "inspection": inspection,
            }
        )

    diagnoses.sort(key=lambda d: d["score"], reverse=True)

    return {
        "equipment_id": equipment_id,
        "diagnoses": diagnoses,
        "primitive_facts": [list(f) for f in sorted(primitive_facts)],
    }
