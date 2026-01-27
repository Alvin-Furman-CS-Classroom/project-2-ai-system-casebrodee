"""
Configuration loading and validation for Module 1.

This module will provide helpers to load and validate:
- global threshold configuration JSON,
- equipment-specific configuration JSON.

Implementation will be filled in when building Module 1.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json


def load_json(path: str | Path) -> Dict[str, Any]:
    """Load a JSON file and return it as a dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_threshold_config(config_path: str | Path) -> Dict[str, Any]:
    """
    Load the global threshold configuration JSON for Module 1.

    For now this is a thin wrapper around `load_json`; validation will be added later.
    """
    return load_json(config_path)


def load_equipment_specs(specs_path: str | Path) -> Dict[str, Any]:
    """
    Load the equipment-specification JSON for Module 1.

    For now this is a thin wrapper around `load_json`; validation will be added later.
    """
    return load_json(specs_path)

