"""
Configuration loading and validation for Module 1.

This module provides helpers to load and validate:
- global threshold configuration JSON,
- equipment-specific configuration JSON.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails."""
    pass


def load_json(path: str | Path) -> Dict[str, Any]:
    """
    Load a JSON file and return it as a dictionary.
    
    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in {path}: {e.msg}",
                e.doc,
                e.pos
            ) from e


def _validate_threshold_value(threshold: Dict[str, Any], sensor_name: str) -> None:
    """
    Validate a single threshold dictionary (e.g., {"min": 20.0, "max": 80.0}).
    
    Raises:
        ConfigValidationError: If validation fails.
    """
    if not isinstance(threshold, dict):
        raise ConfigValidationError(
            f"Threshold for '{sensor_name}' must be a dictionary, got {type(threshold).__name__}"
        )
    
    # Check for valid keys
    valid_keys = {"min", "max"}
    invalid_keys = set(threshold.keys()) - valid_keys
    if invalid_keys:
        raise ConfigValidationError(
            f"Threshold for '{sensor_name}' contains invalid keys: {invalid_keys}. "
            f"Valid keys are: {valid_keys}"
        )
    
    # At least one of min or max must be present
    if not threshold:
        raise ConfigValidationError(
            f"Threshold for '{sensor_name}' is empty. Must contain at least 'min' or 'max'"
        )
    
    # Validate min value
    if "min" in threshold:
        min_val = threshold["min"]
        if not isinstance(min_val, (int, float)):
            raise ConfigValidationError(
                f"Threshold 'min' for '{sensor_name}' must be a number, got {type(min_val).__name__}"
            )
        if not isinstance(min_val, bool):  # bool is a subclass of int, exclude it
            threshold["min"] = float(min_val)
    
    # Validate max value
    if "max" in threshold:
        max_val = threshold["max"]
        if not isinstance(max_val, (int, float)):
            raise ConfigValidationError(
                f"Threshold 'max' for '{sensor_name}' must be a number, got {type(max_val).__name__}"
            )
        if not isinstance(max_val, bool):  # bool is a subclass of int, exclude it
            threshold["max"] = float(max_val)
    
    # Validate min < max if both are present
    if "min" in threshold and "max" in threshold:
        if threshold["min"] >= threshold["max"]:
            raise ConfigValidationError(
                f"Threshold for '{sensor_name}': min ({threshold['min']}) must be less than max ({threshold['max']})"
            )


def validate_threshold_config(config: Dict[str, Any]) -> None:
    """
    Validate the global threshold configuration structure and values.
    
    Checks:
    - Config is a dictionary
    - Each sensor threshold has valid structure
    - Min < max when both are present
    - Values are numeric
    
    Args:
        config: The configuration dictionary to validate.
        
    Raises:
        ConfigValidationError: If validation fails with a descriptive message.
    """
    if not isinstance(config, dict):
        raise ConfigValidationError(
            f"Configuration must be a dictionary, got {type(config).__name__}"
        )
    
    if not config:
        raise ConfigValidationError("Configuration is empty")
    
    # Validate each sensor threshold
    for sensor_name, threshold in config.items():
        if not isinstance(sensor_name, str):
            raise ConfigValidationError(
                f"Sensor name must be a string, got {type(sensor_name).__name__}"
            )
        _validate_threshold_value(threshold, sensor_name)


def validate_equipment_specs(specs: Dict[str, Any]) -> None:
    """
    Validate the equipment specification structure and values.
    
    Checks:
    - Specs is a dictionary
    - Each equipment entry is a dictionary
    - Each equipment's thresholds are valid
    
    Args:
        specs: The equipment specifications dictionary to validate.
        
    Raises:
        ConfigValidationError: If validation fails with a descriptive message.
    """
    if not isinstance(specs, dict):
        raise ConfigValidationError(
            f"Equipment specs must be a dictionary, got {type(specs).__name__}"
        )
    
    # Empty specs are allowed (means no equipment-specific overrides)
    if not specs:
        return
    
    # Validate each equipment entry
    for equipment_id, equipment_config in specs.items():
        if not isinstance(equipment_id, str):
            raise ConfigValidationError(
                f"Equipment ID must be a string, got {type(equipment_id).__name__}"
            )
        
        if not isinstance(equipment_config, dict):
            raise ConfigValidationError(
                f"Equipment config for '{equipment_id}' must be a dictionary, "
                f"got {type(equipment_config).__name__}"
            )
        
        # Validate each sensor threshold for this equipment
        for sensor_name, threshold in equipment_config.items():
            if not isinstance(sensor_name, str):
                raise ConfigValidationError(
                    f"Sensor name in equipment '{equipment_id}' must be a string, "
                    f"got {type(sensor_name).__name__}"
                )
            _validate_threshold_value(threshold, f"{equipment_id}.{sensor_name}")


def load_threshold_config(config_path: str | Path) -> Dict[str, Any]:
    """
    Load and validate the global threshold configuration JSON for Module 1.
    
    The config should have the structure:
    {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0}
    }
    
    Args:
        config_path: Path to the JSON configuration file.
        
    Returns:
        Validated configuration dictionary.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        ConfigValidationError: If validation fails.
    """
    config = load_json(config_path)
    validate_threshold_config(config)
    return config


def load_equipment_specs(specs_path: str | Path) -> Dict[str, Any]:
    """
    Load and validate the equipment-specification JSON for Module 1.
    
    The specs should have the structure:
    {
        "pump_A": {
            "temperature": {"min": 25.0, "max": 75.0},
            "vibration": {"max": 4.5}
        }
    }
    
    Args:
        specs_path: Path to the JSON equipment specifications file.
        
    Returns:
        Validated equipment specifications dictionary.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        ConfigValidationError: If validation fails.
    """
    specs = load_json(specs_path)
    validate_equipment_specs(specs)
    return specs

