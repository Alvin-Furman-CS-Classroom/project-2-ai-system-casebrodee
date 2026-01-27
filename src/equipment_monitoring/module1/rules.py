"""
Rule evaluation utilities for Module 1.

This module implements propositional-logic style rules that operate on a single
sensor reading plus configuration/equipment specs and return which rules are
violated.

Rules are expressed as logical conditions:
- IF sensor_value > max_threshold THEN violation_high
- IF sensor_value < min_threshold THEN violation_low
- IF sensor_value IS MISSING THEN missing_sensor
"""

from __future__ import annotations

from typing import Any, Dict, List


def _get_thresholds(
    sensor_name: str,
    equipment_id: str | None,
    config: Dict[str, Any],
    equipment_specs: Dict[str, Any],
) -> Dict[str, float] | None:
    """
    Get thresholds for a sensor, checking equipment-specific specs first,
    then falling back to global config.

    Returns a dict with 'min' and/or 'max' keys, or None if no thresholds found.
    """
    # Try equipment-specific specs first
    if equipment_id and equipment_id in equipment_specs:
        equipment_config = equipment_specs[equipment_id]
        if sensor_name in equipment_config:
            return equipment_config[sensor_name]

    # Fall back to global config
    if sensor_name in config:
        return config[sensor_name]

    return None


def _parse_sensor_value(value: Any) -> float | None:
    """
    Convert a sensor value to float, handling strings and missing values.

    Returns None if value is missing, empty, or cannot be converted.
    """
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _check_sensor_rule(
    sensor_name: str,
    sensor_value: float | None,
    thresholds: Dict[str, float] | None,
) -> List[str]:
    """
    Check if a sensor value violates thresholds using propositional logic.

    Returns a list of violated rule names (e.g., ["temperature_high"]).
    """
    violations: List[str] = []

    # Rule: IF sensor_value IS MISSING THEN missing_sensor
    if sensor_value is None:
        violations.append(f"missing_{sensor_name}")
        return violations

    # Rule: IF sensor_value > max_threshold THEN sensor_high
    if thresholds and "max" in thresholds:
        if sensor_value > thresholds["max"]:
            violations.append(f"{sensor_name}_high")

    # Rule: IF sensor_value < min_threshold THEN sensor_low
    if thresholds and "min" in thresholds:
        if sensor_value < thresholds["min"]:
            violations.append(f"{sensor_name}_low")

    return violations


def evaluate_rules(
    reading: Dict[str, Any],
    config: Dict[str, Any],
    equipment_specs: Dict[str, Any],
) -> List[str]:
    """
    Evaluate rule violations for a single reading using propositional logic.

    Rules are evaluated as logical conditions:
    - IF temperature > max THEN "temperature_high"
    - IF temperature < min THEN "temperature_low"
    - IF temperature IS MISSING THEN "missing_temperature"
    - Similar rules for pressure and vibration

    Equipment-specific thresholds override global config when available.

    Args:
        reading: Sensor reading dict with keys like 'temperature', 'vibration',
                 'pressure', 'equipment_id', 'timestamp'
        config: Global threshold configuration dict
        equipment_specs: Equipment-specific threshold configuration dict

    Returns:
        List of rule violation identifiers like:
        - "temperature_high"
        - "pressure_low"
        - "vibration_high"
        - "missing_temperature"
    """
    violations: List[str] = []
    equipment_id = reading.get("equipment_id")

    # Check each sensor type
    sensors = ["temperature", "vibration", "pressure"]
    for sensor_name in sensors:
        # Parse the sensor value (CSV values are strings)
        sensor_value = _parse_sensor_value(reading.get(sensor_name))

        # Get thresholds (equipment-specific or global)
        thresholds = _get_thresholds(sensor_name, equipment_id, config, equipment_specs)

        # Evaluate rules for this sensor
        sensor_violations = _check_sensor_rule(sensor_name, sensor_value, thresholds)
        violations.extend(sensor_violations)

    return violations

