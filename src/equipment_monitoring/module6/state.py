"""Map Module 3 diagnosis.json to discrete risk bucket states."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

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
