import json
import pathlib
import pytest

from equipment_monitoring.module1 import config


def test_load_threshold_config_smoke(tmp_path: pathlib.Path) -> None:
    """Smoke test that we can load a simple JSON config file."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text('{"temperature": {"min": 20, "max": 80}}', encoding="utf-8")

    loaded = config.load_threshold_config(cfg_path)

    assert "temperature" in loaded
    assert loaded["temperature"]["min"] == 20.0
    assert loaded["temperature"]["max"] == 80.0


def test_load_threshold_config_valid(tmp_path: pathlib.Path) -> None:
    """Test loading a valid threshold config with multiple sensors."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(
        '{"temperature": {"min": 20.0, "max": 80.0}, '
        '"vibration": {"max": 5.0}, '
        '"pressure": {"min": 10.0, "max": 50.0}}',
        encoding="utf-8"
    )

    loaded = config.load_threshold_config(cfg_path)

    assert loaded["temperature"]["min"] == 20.0
    assert loaded["vibration"]["max"] == 5.0
    assert "min" not in loaded["vibration"]


def test_load_threshold_config_file_not_found(tmp_path: pathlib.Path) -> None:
    """Test that missing file raises FileNotFoundError."""
    cfg_path = tmp_path / "nonexistent.json"

    with pytest.raises(FileNotFoundError):
        config.load_threshold_config(cfg_path)


def test_load_threshold_config_invalid_json(tmp_path: pathlib.Path) -> None:
    """Test that invalid JSON raises JSONDecodeError."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text('{"temperature": {invalid}', encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        config.load_threshold_config(cfg_path)


def test_validate_threshold_config_min_greater_than_max() -> None:
    """Test validation fails when min >= max."""
    invalid_config = {"temperature": {"min": 80.0, "max": 20.0}}

    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_threshold_config(invalid_config)
    
    assert "min" in str(exc_info.value).lower()
    assert "max" in str(exc_info.value).lower()


def test_validate_threshold_config_min_equals_max() -> None:
    """Test validation fails when min == max."""
    invalid_config = {"temperature": {"min": 50.0, "max": 50.0}}

    with pytest.raises(config.ConfigValidationError):
        config.validate_threshold_config(invalid_config)


def test_validate_threshold_config_invalid_type() -> None:
    """Test validation fails when config is not a dictionary."""
    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_threshold_config([])
    
    assert "dictionary" in str(exc_info.value).lower()


def test_validate_threshold_config_empty() -> None:
    """Test validation fails when config is empty."""
    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_threshold_config({})
    
    assert "empty" in str(exc_info.value).lower()


def test_validate_threshold_config_non_numeric_min() -> None:
    """Test validation fails when min is not a number."""
    invalid_config = {"temperature": {"min": "20", "max": 80.0}}

    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_threshold_config(invalid_config)
    
    assert "number" in str(exc_info.value).lower()


def test_validate_threshold_config_non_numeric_max() -> None:
    """Test validation fails when max is not a number."""
    invalid_config = {"temperature": {"min": 20.0, "max": "80"}}

    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_threshold_config(invalid_config)
    
    assert "number" in str(exc_info.value).lower()


def test_validate_threshold_config_invalid_keys() -> None:
    """Test validation fails when threshold has invalid keys."""
    invalid_config = {"temperature": {"min": 20.0, "max": 80.0, "invalid": 5.0}}

    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_threshold_config(invalid_config)
    
    assert "invalid" in str(exc_info.value).lower()


def test_validate_threshold_config_empty_threshold() -> None:
    """Test validation fails when threshold dictionary is empty."""
    invalid_config = {"temperature": {}}

    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_threshold_config(invalid_config)
    
    assert "empty" in str(exc_info.value).lower()


def test_validate_threshold_config_only_min() -> None:
    """Test that threshold with only min is valid."""
    valid_config = {"temperature": {"min": 20.0}}
    # Should not raise
    config.validate_threshold_config(valid_config)


def test_validate_threshold_config_only_max() -> None:
    """Test that threshold with only max is valid."""
    valid_config = {"vibration": {"max": 5.0}}
    # Should not raise
    config.validate_threshold_config(valid_config)


def test_load_equipment_specs_valid(tmp_path: pathlib.Path) -> None:
    """Test loading valid equipment specs."""
    specs_path = tmp_path / "specs.json"
    specs_path.write_text(
        '{"pump_A": {"temperature": {"min": 25.0, "max": 75.0}}, '
        '"pump_B": {"vibration": {"max": 4.5}}}',
        encoding="utf-8"
    )

    loaded = config.load_equipment_specs(specs_path)

    assert "pump_A" in loaded
    assert loaded["pump_A"]["temperature"]["min"] == 25.0
    assert "pump_B" in loaded


def test_load_equipment_specs_empty(tmp_path: pathlib.Path) -> None:
    """Test that empty equipment specs are allowed."""
    specs_path = tmp_path / "specs.json"
    specs_path.write_text("{}", encoding="utf-8")

    loaded = config.load_equipment_specs(specs_path)

    assert loaded == {}


def test_validate_equipment_specs_invalid_equipment_config() -> None:
    """Test validation fails when equipment config is not a dictionary."""
    invalid_specs = {"pump_A": "not a dict"}

    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_equipment_specs(invalid_specs)
    
    assert "dictionary" in str(exc_info.value).lower()


def test_validate_equipment_specs_invalid_threshold() -> None:
    """Test validation fails when equipment has invalid threshold."""
    invalid_specs = {"pump_A": {"temperature": {"min": 80.0, "max": 20.0}}}

    with pytest.raises(config.ConfigValidationError):
        config.validate_equipment_specs(invalid_specs)


def test_validate_equipment_specs_non_string_equipment_id() -> None:
    """Test validation fails when equipment ID is not a string."""
    invalid_specs = {123: {"temperature": {"min": 20.0, "max": 80.0}}}

    with pytest.raises(config.ConfigValidationError) as exc_info:
        config.validate_equipment_specs(invalid_specs)
    
    assert "string" in str(exc_info.value).lower()


def test_load_threshold_config_with_validation_error(tmp_path: pathlib.Path) -> None:
    """Test that load_threshold_config raises ConfigValidationError on invalid config."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text('{"temperature": {"min": 80, "max": 20}}', encoding="utf-8")

    with pytest.raises(config.ConfigValidationError):
        config.load_threshold_config(cfg_path)

