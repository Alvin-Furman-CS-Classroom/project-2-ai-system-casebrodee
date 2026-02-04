from equipment_monitoring.module1 import classifier


def test_classify_reading_basic_shape() -> None:
    """Classifier should return the required keys."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
    }
    cfg = {}
    specs = {}

    result = classifier.classify_reading(reading, cfg, specs)

    assert result["timestamp"] == reading["timestamp"]
    assert result["equipment_id"] == reading["equipment_id"]
    assert "status" in result
    assert "violated_rules" in result
    assert "confidence" in result


def test_classify_reading_confidence_normal_when_no_violations() -> None:
    """When there are no violations, status should be normal with high confidence."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
    }
    cfg = {}
    specs = {}

    result = classifier.classify_reading(reading, cfg, specs)

    assert result["status"] == "normal"
    assert result["violated_rules"] == []
    assert result["confidence"] == 1.0


def test_classify_reading_confidence_increases_with_more_violations(monkeypatch) -> None:
    """More violations should produce higher anomaly confidence (heuristic)."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
    }
    cfg = {}
    specs = {}

    # Patch evaluate_rules to control violations
    def fake_evaluate_rules_one(*_args, **_kwargs):
        return ["temperature_high"]

    def fake_evaluate_rules_three(*_args, **_kwargs):
        return ["temperature_high", "pressure_low", "vibration_high"]

    # One violation
    monkeypatch.setattr(
        "equipment_monitoring.module1.classifier.rules.evaluate_rules",
        fake_evaluate_rules_one,
    )
    result_one = classifier.classify_reading(reading, cfg, specs)

    # Three violations
    monkeypatch.setattr(
        "equipment_monitoring.module1.classifier.rules.evaluate_rules",
        fake_evaluate_rules_three,
    )
    result_three = classifier.classify_reading(reading, cfg, specs)

    assert result_one["status"] == "anomaly"
    assert result_three["status"] == "anomaly"
    assert result_three["confidence"] > result_one["confidence"]


def test_classify_reading_confidence_reduced_when_missing_values(monkeypatch) -> None:
    """Presence of missing_* rules should reduce anomaly confidence."""
    reading = {
        "timestamp": "2026-01-01T00:00:00Z",
        "equipment_id": "pump_A",
    }
    cfg = {}
    specs = {}

    def fake_evaluate_rules_no_missing(*_args, **_kwargs):
        return ["temperature_high"]

    def fake_evaluate_rules_with_missing(*_args, **_kwargs):
        return ["temperature_high", "missing_pressure"]

    monkeypatch.setattr(
        "equipment_monitoring.module1.classifier.rules.evaluate_rules",
        fake_evaluate_rules_no_missing,
    )
    result_no_missing = classifier.classify_reading(reading, cfg, specs)

    monkeypatch.setattr(
        "equipment_monitoring.module1.classifier.rules.evaluate_rules",
        fake_evaluate_rules_with_missing,
    )
    result_with_missing = classifier.classify_reading(reading, cfg, specs)

    assert result_with_missing["confidence"] < result_no_missing["confidence"]

