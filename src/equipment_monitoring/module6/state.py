"""Map Module 3 diagnosis.json (and optional Module 1 classifications) to MDP start states."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

from ..module4.loader import Module4ConfigError, load_equipment_risks
from .loader import Module6ConfigError


def risk_scalar_to_bucket(risk: float, thresholds: Tuple[float, float]) -> str:
    """
    Map risk in [0,1] to risk_low | risk_mid | risk_high.

    thresholds: (t_low_mid, t_mid_high) with 0 <= t_low_mid <= t_mid_high <= 1.
    [0, t0) -> risk_low, [t0, t1) -> risk_mid, [t1, 1] -> risk_high.
    """
    t0, t1 = thresholds
    r = max(0.0, min(1.0, float(risk)))
    if r < t0:
        return "risk_low"
    if r < t1:
        return "risk_mid"
    return "risk_high"


def _diagnosis_m1_confidence_by_equipment(diagnosis_path: Path) -> Dict[str, float]:
    try:
        with open(diagnosis_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise Module6ConfigError(f"Cannot read diagnosis for M1 meta ({diagnosis_path}): {e}") from e
    blocks = data.get("equipment")
    if not isinstance(blocks, list):
        return {}
    out: Dict[str, float] = {}
    for b in blocks:
        if not isinstance(b, dict):
            continue
        eid = b.get("equipment_id")
        if not eid:
            continue
        meta = b.get("meta") or {}
        if isinstance(meta, dict) and "m1_max_confidence" in meta:
            try:
                out[str(eid)] = max(0.0, min(1.0, float(meta["m1_max_confidence"])))
            except (TypeError, ValueError):
                out[str(eid)] = 0.0
        else:
            out[str(eid)] = 0.0
    return out


def _classification_anomaly_rate(classifications_path: Path, equipment_id: str) -> float | None:
    """Fraction of rows with status anomaly for this equipment; None if no rows."""
    rows: List[Mapping[str, object]] = []
    try:
        with open(classifications_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        return None
    mine = [r for r in rows if str(r.get("equipment_id", "")) == equipment_id]
    if not mine:
        return None
    n_anom = sum(1 for r in mine if str(r.get("status", "")).lower() == "anomaly")
    return n_anom / float(len(mine))


def equipment_m1_alert(
    equipment_id: str,
    *,
    classifications_path: Path | None,
    m1_anomaly_rate_alert: float,
    diagnosis_m1_by_eq: Mapping[str, float],
    m1_confidence_alert_fallback: float,
) -> bool:
    """
    True if Module 1 style activity suggests elevated alert for this equipment.

    Uses classifications.jsonl anomaly rate when the file exists and has rows
    for this equipment; otherwise falls back to diagnosis meta m1_max_confidence.
    """
    if classifications_path is not None and classifications_path.is_file():
        rate = _classification_anomaly_rate(classifications_path, equipment_id)
        if rate is not None:
            return rate >= m1_anomaly_rate_alert
    conf = diagnosis_m1_by_eq.get(str(equipment_id), 0.0)
    return conf >= m1_confidence_alert_fallback


def mdp_supports_m1hot_rich_states(mdp_states: Sequence[str]) -> bool:
    """True if MDP includes *_m1hot variants (paired with base risk buckets)."""
    return any(s.endswith("_m1hot") for s in mdp_states)


def equipment_mdp_start_states(
    diagnosis_path: str | Path,
    thresholds: Tuple[float, float],
    mdp_states: Sequence[str],
    *,
    classifications_path: Path | None,
    m1_anomaly_rate_alert: float,
    m1_confidence_alert_fallback: float,
) -> List[str]:
    """
    One MDP start state per equipment (same order as load_equipment_risks).

    With a 6-state MDP (risk × m1hot), each equipment maps to ``risk_*`` or
    ``risk_*_m1hot`` based on diagnosis bucket and M1 alert signal.

    With a 3-state MDP, returns plain ``risk_low`` / ``risk_mid`` / ``risk_high``.
    """
    path = Path(diagnosis_path)
    try:
        risks = load_equipment_risks(path)
    except Module4ConfigError as e:
        raise Module6ConfigError(f"Invalid diagnosis.json for Module 6 ({path}): {e}") from e

    rich = mdp_supports_m1hot_rich_states(mdp_states)
    m1_by_eq = _diagnosis_m1_confidence_by_equipment(path) if rich else {}

    out: List[str] = []
    for er in risks:
        bucket = risk_scalar_to_bucket(er.risk, thresholds)
        if not rich:
            sid = bucket
        else:
            hot_suffix = f"{bucket}_m1hot"
            if hot_suffix not in mdp_states:
                sid = bucket
            else:
                hot = equipment_m1_alert(
                    er.equipment_id,
                    classifications_path=classifications_path,
                    m1_anomaly_rate_alert=m1_anomaly_rate_alert,
                    diagnosis_m1_by_eq=m1_by_eq,
                    m1_confidence_alert_fallback=m1_confidence_alert_fallback,
                )
                sid = hot_suffix if hot else bucket
        if sid not in mdp_states:
            raise Module6ConfigError(
                f"derived start state {sid!r} for equipment {er.equipment_id!r} is not in mdp.states"
            )
        out.append(sid)
    return out


def equipment_risk_buckets(diagnosis_path: str | Path, thresholds: Tuple[float, float]) -> List[str]:
    """
    Return one risk bucket string per equipment row in diagnosis.json (same order as load_equipment_risks).

    Args:
        diagnosis_path: Path to Module 3 ``diagnosis.json``.
        thresholds: ``(t_low_mid, t_mid_high)`` for :func:`risk_scalar_to_bucket`.

    Returns:
        List of state keys (e.g. ``risk_low``), one per equipment block.

    Raises:
        Module6ConfigError: If the file is not valid diagnosis JSON or fails Module 4 loader checks.
    """
    path = Path(diagnosis_path)
    try:
        risks = load_equipment_risks(path)
    except Module4ConfigError as e:
        raise Module6ConfigError(f"Invalid diagnosis.json for Module 6 ({path}): {e}") from e
    return [risk_scalar_to_bucket(er.risk, thresholds) for er in risks]
