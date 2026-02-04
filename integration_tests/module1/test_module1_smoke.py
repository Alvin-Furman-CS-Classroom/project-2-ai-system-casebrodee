import json
from pathlib import Path

from equipment_monitoring.module1 import classifier


def test_module1_smoke(tmp_path: Path) -> None:
    """
    Smoke test that runs the Module 1 pipeline end-to-end on a tiny dataset.

    Tests that the full pipeline works: config loading, rule evaluation,
    classification, and output generation.
    """
    cfg_path = tmp_path / "config.json"
    specs_path = tmp_path / "specs.json"
    csv_path = tmp_path / "readings.csv"
    output_dir = tmp_path / "outputs"

    # Create config with thresholds
    config = {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0},
    }
    cfg_path.write_text(json.dumps(config), encoding="utf-8")

    # Empty equipment specs (use global config)
    specs_path.write_text("{}", encoding="utf-8")

    # Create CSV with both normal and anomalous readings
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure\n"
        "2026-01-01T00:00:00Z,pump_A,30,2.0,20\n"  # Normal
        "2026-01-01T00:01:00Z,pump_A,85,6.0,8\n",  # Anomaly: temp high, vib high, pressure low
        encoding="utf-8",
    )

    classifier.run_module1(
        config_path=cfg_path,
        specs_path=specs_path,
        csv_path=csv_path,
        output_dir=output_dir,
    )

    # Verify outputs exist
    assert (output_dir / "classifications.jsonl").exists()
    assert (output_dir / "alerts.txt").exists()

    # Verify classifications content
    classifications_path = output_dir / "classifications.jsonl"
    classifications = []
    with open(classifications_path, "r", encoding="utf-8") as f:
        for line in f:
            classifications.append(json.loads(line))

    assert len(classifications) == 2

    # First reading should be normal
    assert classifications[0]["status"] == "normal"
    assert classifications[0]["violated_rules"] == []

    # Second reading should be anomaly with violations
    assert classifications[1]["status"] == "anomaly"
    assert "temperature_high" in classifications[1]["violated_rules"]
    assert "vibration_high" in classifications[1]["violated_rules"]
    assert "pressure_low" in classifications[1]["violated_rules"]
    assert classifications[1]["confidence"] > 0.5

    # Verify alerts file has content for the anomaly
    alerts_path = output_dir / "alerts.txt"
    alerts_content = alerts_path.read_text(encoding="utf-8")
    assert "temperature_high" in alerts_content
    assert "pump_A" in alerts_content


def test_module1_with_equipment_specific_thresholds(tmp_path: Path) -> None:
    """
    Integration test that equipment-specific thresholds affect violations.

    Uses stricter equipment-specific limits than the global config and checks
    that violations are raised according to the equipment-specific rules.
    """
    cfg_path = tmp_path / "config.json"
    specs_path = tmp_path / "specs.json"
    csv_path = tmp_path / "readings.csv"
    output_dir = tmp_path / "outputs"

    # Global config (looser)
    config_data = {
        "temperature": {"min": 20.0, "max": 80.0},
    }
    cfg_path.write_text(json.dumps(config_data), encoding="utf-8")

    # Equipment-specific config (stricter for pump_A)
    specs_data = {
        "pump_A": {
            "temperature": {"min": 25.0, "max": 60.0},
        }
    }
    specs_path.write_text(json.dumps(specs_data), encoding="utf-8")

    # Temperature 65 is fine under global config (max 80), but violates pump_A max 60
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure\n"
        "2026-01-01T00:00:00Z,pump_A,65,2.0,20\n",
        encoding="utf-8",
    )

    classifier.run_module1(
        config_path=cfg_path,
        specs_path=specs_path,
        csv_path=csv_path,
        output_dir=output_dir,
    )

    classifications_path = output_dir / "classifications.jsonl"
    with open(classifications_path, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f]

    assert len(lines) == 1
    assert lines[0]["status"] == "anomaly"
    assert "temperature_high" in lines[0]["violated_rules"]
