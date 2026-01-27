import pathlib

from equipment_monitoring.module1 import config


def test_load_threshold_config_smoke(tmp_path: pathlib.Path) -> None:
    """Smoke test that we can load a simple JSON config file."""
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text('{"temperature": {"min": 20, "max": 80}}', encoding="utf-8")

    loaded = config.load_threshold_config(cfg_path)

    assert "temperature" in loaded

