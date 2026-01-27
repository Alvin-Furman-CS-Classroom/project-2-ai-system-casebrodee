"""
Rule evaluation utilities for Module 1.

This module will hold propositional-logic style rules that operate on a single
sensor reading plus configuration/equipment specs and return which rules are
violated.

The concrete rule set and inference details will be implemented later.
"""

from __future__ import annotations

from typing import Any, Dict, List


def evaluate_rules(
    reading: Dict[str, Any],
    config: Dict[str, Any],
    equipment_specs: Dict[str, Any],
) -> List[str]:
    """
    Evaluate rule violations for a single reading.

    Returns a list of rule identifiers like:
    - "temperature_high"
    - "pressure_low"
    - "vibration_high"
    - "missing_temperature"

    The implementation will be added in the Module 1 coding phase.
    """
    # Placeholder implementation – to be filled in later.
    return []

