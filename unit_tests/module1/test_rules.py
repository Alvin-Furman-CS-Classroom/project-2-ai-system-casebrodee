from equipment_monitoring.module1 import rules


def test_evaluate_rules_returns_list() -> None:
    """Ensure the function returns a list."""
    reading = {}
    cfg = {}
    specs = {}

    result = rules.evaluate_rules(reading, cfg, specs)

    assert isinstance(result, list)


def test_evaluate_rules_normal_reading() -> None:
    """Test that normal readings within thresholds return no violations."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
        "temperature": "30.0",
        "vibration": "2.0",
        "pressure": "25.0",
    }
    cfg = {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0},
    }
    specs = {}

    result = rules.evaluate_rules(reading, cfg, specs)

    assert result == []


def test_evaluate_rules_temperature_high() -> None:
    """Test detection of high temperature violation."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
        "temperature": "85.0",  # Above max of 80
        "vibration": "2.0",
        "pressure": "25.0",
    }
    cfg = {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0},
    }
    specs = {}

    result = rules.evaluate_rules(reading, cfg, specs)

    assert "temperature_high" in result
    assert len(result) == 1


def test_evaluate_rules_pressure_low() -> None:
    """Test detection of low pressure violation."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
        "temperature": "30.0",
        "vibration": "2.0",
        "pressure": "8.0",  # Below min of 10
    }
    cfg = {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0},
    }
    specs = {}

    result = rules.evaluate_rules(reading, cfg, specs)

    assert "pressure_low" in result
    assert len(result) == 1


def test_evaluate_rules_multiple_violations() -> None:
    """Test detection of multiple rule violations."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
        "temperature": "85.0",  # High
        "vibration": "6.0",  # High
        "pressure": "8.0",  # Low
    }
    cfg = {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0},
    }
    specs = {}

    result = rules.evaluate_rules(reading, cfg, specs)

    assert "temperature_high" in result
    assert "vibration_high" in result
    assert "pressure_low" in result
    assert len(result) == 3


def test_evaluate_rules_missing_sensor() -> None:
    """Test detection of missing sensor values."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
        "temperature": "",  # Missing
        "vibration": "2.0",
        "pressure": "25.0",
    }
    cfg = {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0},
    }
    specs = {}

    result = rules.evaluate_rules(reading, cfg, specs)

    assert "missing_temperature" in result
    assert len(result) == 1


def test_evaluate_rules_equipment_specific_thresholds() -> None:
    """Test that equipment-specific thresholds override global config."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
        "temperature": "30.0",  # Within global (20-80) but above equipment-specific (25-75)
        "vibration": "2.0",
        "pressure": "25.0",
    }
    cfg = {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0},
    }
    specs = {
        "pump_A": {
            "temperature": {"min": 25.0, "max": 75.0},  # Stricter than global
        }
    }

    result = rules.evaluate_rules(reading, cfg, specs)

    # Should be normal because 30 is within equipment-specific range (25-75)
    assert result == []


def test_evaluate_rules_equipment_specific_violation() -> None:
    """Test that equipment-specific thresholds can detect violations."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
        "temperature": "76.0",  # Within global (20-80) but above equipment-specific (25-75)
        "vibration": "2.0",
        "pressure": "25.0",
    }
    cfg = {
        "temperature": {"min": 20.0, "max": 80.0},
        "vibration": {"max": 5.0},
        "pressure": {"min": 10.0, "max": 50.0},
    }
    specs = {
        "pump_A": {
            "temperature": {"min": 25.0, "max": 75.0},
        }
    }

    result = rules.evaluate_rules(reading, cfg, specs)

    assert "temperature_high" in result

