"""Module 3 batch runner: KB + Module 1/2 artifacts -> diagnosis JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from .diagnosis import build_diagnosis_record
from .facts import build_facts_per_equipment
from .kb_loader import load_kb, rules_by_id
from .logic import Atom, forward_chain


def infer_batch(
    kb_path: str | Path,
    classifications_path: str | Path,
    sequences_path: str | Path,
    warning_signs_path: str | Path,
) -> Dict[str, Any]:
    """
    Run forward chaining for every equipment_id found in classifications.

    Returns a dict suitable for JSON serialization with key ``equipment``.
    """
    rules = load_kb(kb_path)
    r_index = rules_by_id(rules)

    per_eq, meta = build_facts_per_equipment(
        classifications_path, sequences_path, warning_signs_path
    )

    equipment_out: List[Dict[str, Any]] = []

    for eid in sorted(per_eq.keys()):
        primitive: Set[Atom] = set(per_eq[eid])
        closed, provenance = forward_chain(primitive, rules)
        m = meta[eid]
        record = build_diagnosis_record(
            equipment_id=eid,
            closed_facts=closed,
            provenance=provenance,
            primitive_facts=primitive,
            rules_index=r_index,
            m1_max_confidence=float(m["m1_max_confidence"]),
            m2_top_predictive=float(m["m2_top_predictive"]),
        )
        record["meta"] = {
            "m1_max_confidence": m["m1_max_confidence"],
            "m2_top_predictive": m["m2_top_predictive"],
            "m2_on_failure_path": m["m2_on_failure_path"],
            "violated_rules": m["violated_rules"],
        }
        equipment_out.append(record)

    return {"equipment": equipment_out}


def run_module3(
    kb_path: str | Path,
    classifications_path: str | Path,
    sequences_path: str | Path,
    warning_signs_path: str | Path,
    output_dir: str | Path,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = infer_batch(
        kb_path=kb_path,
        classifications_path=classifications_path,
        sequences_path=sequences_path,
        warning_signs_path=warning_signs_path,
    )

    out_path = output_dir / "diagnosis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    n = sum(1 for e in result["equipment"] if e.get("diagnoses"))
    print(f"Module 3 wrote {out_path} ({len(result['equipment'])} equipment, {n} with diagnoses).")
