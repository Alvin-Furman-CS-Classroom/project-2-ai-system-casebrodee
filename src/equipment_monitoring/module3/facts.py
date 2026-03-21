"""Build ground facts from Module 1 and Module 2 artifacts (batch per equipment)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from .logic import Atom

PrimitiveFactMeta = Dict[str, Any]


def _load_jsonl_classifications(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_facts_per_equipment(
    classifications_path: str | Path,
    sequences_path: str | Path,
    warning_signs_path: str | Path,
) -> Tuple[Dict[str, Set[Atom]], Dict[str, PrimitiveFactMeta]]:
    """
    Aggregate readings by equipment_id and emit ground atoms plus metadata for scoring.

    Module 2 inputs are required: sequences.json and warning_signs.json.
    """
    classifications_path = Path(classifications_path)
    sequences_path = Path(sequences_path)
    warning_signs_path = Path(warning_signs_path)

    rows = _load_jsonl_classifications(classifications_path)
    seq_data = _load_json(sequences_path)
    warn_data = _load_json(warning_signs_path)

    sequences = seq_data.get("sequences") or []
    warning_signs = warn_data.get("warning_signs") or []

    top_predictive = 0.0
    if warning_signs:
        top_predictive = float(warning_signs[0].get("predictive_score", 0.0))

    # equipment -> max sequence frequency where that equipment appears
    m2_freq: Dict[str, int] = {}
    m2_on_path: Set[str] = set()
    for seq in sequences:
        if not isinstance(seq, dict):
            continue
        freq = int(seq.get("frequency", 0))
        machines = seq.get("machines") or []
        for mid in machines:
            m2_on_path.add(str(mid))
            m2_freq[mid] = max(m2_freq.get(mid, 0), freq)

    by_eq: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        eid = row.get("equipment_id")
        if eid is None:
            continue
        eid = str(eid)
        by_eq.setdefault(eid, []).append(row)

    per_equipment: Dict[str, Set[Atom]] = {}
    meta: Dict[str, PrimitiveFactMeta] = {}

    for eid, erows in by_eq.items():
        facts: Set[Atom] = set()
        violated: Set[str] = set()
        max_conf = 0.0
        any_anomaly = False

        for row in erows:
            conf = float(row.get("confidence", 0.0))
            max_conf = max(max_conf, conf)
            if row.get("status") == "anomaly":
                any_anomaly = True
            for vr in row.get("violated_rules") or []:
                violated.add(str(vr))

        status = "anomaly" if any_anomaly else "normal"
        facts.add(("status", eid, status))
        for vr in sorted(violated):
            facts.add(("violated", eid, vr))

        facts.add(("m1_max_confidence", eid, f"{max_conf:.6f}".rstrip("0").rstrip(".")))

        if eid in m2_on_path:
            facts.add(("m2_on_failure_path", eid))
            facts.add(("m2_sequence_freq", eid, str(m2_freq.get(eid, 0))))
            facts.add(("m2_top_predictive", eid, str(top_predictive)))
        else:
            facts.add(("m2_sequence_freq", eid, "0"))
            facts.add(("m2_top_predictive", eid, "0"))

        per_equipment[eid] = facts
        meta[eid] = {
            "m1_max_confidence": max_conf,
            "m2_top_predictive": top_predictive if eid in m2_on_path else 0.0,
            "m2_on_failure_path": eid in m2_on_path,
            "violated_rules": sorted(violated),
        }

    return per_equipment, meta
