"""Load Module 3 diagnosis and Module 4 maintenance configuration JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class MaintenanceAction:
    id: str
    cost: float
    downtime_hours: float
    risk_multiplier: float


@dataclass(frozen=True)
class EquipmentRisk:
    equipment_id: str
    risk: float


@dataclass(frozen=True)
class Module4Config:
    actions: Tuple[MaintenanceAction, ...]
    budget: float
    max_total_downtime_hours: float
    failure_cost_scale: float
    hill_climbing_max_iterations: int
    hill_climbing_restarts: int
    sa_initial_temp: float
    sa_cooling_rate: float
    sa_max_iterations: int


class Module4ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ProductionSchedule:
    """Optional production context: tighten aggregate downtime vs base Module 4 config."""

    label: str
    notes: str
    max_total_downtime_hours: float | None


def _load_json_object(path: Path, label: str) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise Module4ConfigError(f"{label} is not valid JSON ({path}): {e}") from e


def load_production_schedule(path: str | Path) -> ProductionSchedule:
    p = Path(path)
    data = _load_json_object(p, "production schedule file")
    if not isinstance(data, dict):
        raise Module4ConfigError("production schedule must be a JSON object")
    label = data.get("label") or ""
    if not isinstance(label, str):
        label = str(label)
    notes = data.get("notes") or ""
    if not isinstance(notes, str):
        notes = str(notes)
    raw_cap = data.get("max_total_downtime_hours")
    cap: float | None
    if raw_cap is None:
        cap = None
    else:
        try:
            cap = float(raw_cap)
        except (TypeError, ValueError) as e:
            raise Module4ConfigError(f"max_total_downtime_hours invalid: {e}") from e
        if cap < 0:
            raise Module4ConfigError("max_total_downtime_hours must be non-negative")
    return ProductionSchedule(label=label, notes=notes, max_total_downtime_hours=cap)


def apply_production_downtime_cap(
    config: Module4Config,
    schedule: ProductionSchedule | None,
) -> tuple[Module4Config, dict]:
    """
    If schedule specifies max_total_downtime_hours, effective cap is
    min(config.max_total_downtime_hours, schedule cap).
    Returns (possibly updated config, meta dict for JSON output).
    """
    if schedule is None:
        return config, {"applied": False}
    if schedule.max_total_downtime_hours is None:
        return config, {
            "applied": True,
            "label": schedule.label,
            "notes": schedule.notes,
            "cap_source": "none",
        }
    effective = min(config.max_total_downtime_hours, schedule.max_total_downtime_hours)
    new_cfg = replace(config, max_total_downtime_hours=effective)
    meta = {
        "applied": True,
        "label": schedule.label,
        "notes": schedule.notes,
        "cap_source": "production_schedule",
        "base_max_total_downtime_hours": config.max_total_downtime_hours,
        "schedule_max_total_downtime_hours": schedule.max_total_downtime_hours,
        "effective_max_total_downtime_hours": effective,
    }
    return new_cfg, meta


def load_module4_config(path: str | Path) -> Module4Config:
    p = Path(path)
    data = _load_json_object(p, "Module 4 config file")

    raw_actions = data.get("actions")
    if not isinstance(raw_actions, list) or not raw_actions:
        raise Module4ConfigError("config must contain non-empty 'actions' array")

    actions: List[MaintenanceAction] = []
    seen_ids: set[str] = set()
    for i, a in enumerate(raw_actions):
        if not isinstance(a, dict):
            raise Module4ConfigError(f"actions[{i}] must be an object")
        aid = a.get("id")
        if not aid or not isinstance(aid, str):
            raise Module4ConfigError(f"actions[{i}] missing string 'id'")
        if aid in seen_ids:
            raise Module4ConfigError(f"duplicate action id: {aid}")
        seen_ids.add(aid)
        try:
            actions.append(
                MaintenanceAction(
                    id=aid,
                    cost=float(a["cost"]),
                    downtime_hours=float(a["downtime_hours"]),
                    risk_multiplier=float(a["risk_multiplier"]),
                )
            )
        except (KeyError, TypeError, ValueError) as e:
            raise Module4ConfigError(f"actions[{i}] invalid numeric fields: {e}") from e

    try:
        budget = float(data["budget"])
        max_dt = float(data["max_total_downtime_hours"])
        failure_scale = float(data["failure_cost_scale"])
    except (KeyError, TypeError, ValueError) as e:
        raise Module4ConfigError(f"missing or invalid budget/downtime/failure_cost_scale: {e}") from e

    hc = data.get("hill_climbing", {})
    sa = data.get("simulated_annealing", {})

    def _int(d: Dict[str, Any], key: str, default: int) -> int:
        v = d.get(key, default)
        if v is None:
            return default
        return int(v)

    def _float(d: Dict[str, Any], key: str, default: float) -> float:
        v = d.get(key, default)
        if v is None:
            return float(default)
        return float(v)

    return Module4Config(
        actions=tuple(actions),
        budget=budget,
        max_total_downtime_hours=max_dt,
        failure_cost_scale=failure_scale,
        hill_climbing_max_iterations=max(1, _int(hc, "max_iterations", 2000)),
        hill_climbing_restarts=max(1, _int(hc, "restarts", 5)),
        sa_initial_temp=max(1e-6, _float(sa, "initial_temp", 2.0)),
        sa_cooling_rate=min(0.99999, max(0.5, _float(sa, "cooling_rate", 0.995))),
        sa_max_iterations=max(1, _int(sa, "max_iterations", 4000)),
    )


def load_equipment_risks(diagnosis_path: str | Path) -> List[EquipmentRisk]:
    p = Path(diagnosis_path)
    data = _load_json_object(p, "diagnosis.json")

    blocks = data.get("equipment")
    if not isinstance(blocks, list):
        raise Module4ConfigError("diagnosis.json must contain 'equipment' array")

    out: List[EquipmentRisk] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        eid = b.get("equipment_id")
        if not eid:
            continue
        diagnoses = b.get("diagnoses") or []
        if isinstance(diagnoses, list) and diagnoses:
            scores = [float(d["score"]) for d in diagnoses if isinstance(d, dict) and "score" in d]
            r = max(scores) if scores else 0.0
        else:
            meta = b.get("meta") or {}
            m1 = float(meta.get("m1_max_confidence", 0) or 0)
            m2 = float(meta.get("m2_top_predictive", 0) or 0)
            r = 0.5 * m1 + 0.5 * m2
        r = max(0.0, min(1.0, r))
        out.append(EquipmentRisk(equipment_id=str(eid), risk=r))

    out.sort(key=lambda x: x.equipment_id)
    return out
