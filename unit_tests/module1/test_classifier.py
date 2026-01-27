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

