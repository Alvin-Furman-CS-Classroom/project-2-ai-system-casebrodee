from equipment_monitoring.module1 import rules


def test_evaluate_rules_returns_list() -> None:
    """For now, just ensure the placeholder returns a list."""
    reading = {}
    cfg = {}
    specs = {}

    result = rules.evaluate_rules(reading, cfg, specs)

    assert isinstance(result, list)

