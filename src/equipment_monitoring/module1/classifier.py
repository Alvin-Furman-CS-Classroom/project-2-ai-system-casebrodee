"""
High-level per-reading classifier for Module 1.

This module will expose the main public interfaces used by later modules:
- `classify_reading(reading, config, specs) -> dict`
- `run_module1(config_path, specs_path, csv_path, output_dir) -> None`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from . import config as config_module
from . import rules
from . import io


def classify_reading(
    reading: Dict[str, Any],
    config: Dict[str, Any],
    equipment_specs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Classify a single sensor reading.

    Returns a dictionary with at least:
    - timestamp
    - equipment_id
    - status: "normal" or "anomaly"
    - violated_rules: list of strings
    - confidence: float between 0 and 1

    Implementation will be completed in the Module 1 coding phase.
    """
    violated_rules = rules.evaluate_rules(reading, config, equipment_specs)
    status = "anomaly" if violated_rules else "normal"

    # Calculate confidence based on number and type of violations
    # More violations = higher confidence it's an anomaly
    # Missing sensor values = lower confidence (could be data issue)
    if not violated_rules:
        confidence = 1.0  # High confidence in normal status
    else:
        num_violations = len(violated_rules)
        has_missing = any("missing_" in rule for rule in violated_rules)
        
        # Base confidence: 0.7 for single violation, up to 0.95 for multiple
        base_confidence = min(0.7 + (num_violations - 1) * 0.1, 0.95)
        
        # Reduce confidence if missing sensors (could be data quality issue)
        if has_missing:
            confidence = base_confidence * 0.8
        else:
            confidence = base_confidence

    result = {
        "timestamp": reading.get("timestamp"),
        "equipment_id": reading.get("equipment_id"),
        "status": status,
        "violated_rules": violated_rules,
        "confidence": confidence,
    }
    return result


def run_module1(
    config_path: str | Path,
    specs_path: str | Path,
    csv_path: str | Path,
    output_dir: str | Path,
) -> None:
    """
    Run the full Module 1 pipeline on the given inputs and write outputs.

    - Loads configuration and equipment specs.
    - Streams readings from the CSV.
    - Classifies each reading.
    - Writes JSONL and alert text outputs to `output_dir`.
    """
    cfg = config_module.load_threshold_config(config_path)
    specs = config_module.load_equipment_specs(specs_path)

    readings = io.read_readings_csv(csv_path)

    classified = [
        classify_reading(reading, cfg, specs) for reading in readings
    ]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    io.write_classifications_jsonl(
        classified, output_dir / "classifications.jsonl"
    )
    io.write_alerts_text(classified, output_dir / "alerts.txt")

