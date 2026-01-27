from pathlib import Path

from equipment_monitoring.module1 import classifier


def test_module1_smoke(tmp_path: Path) -> None:
    """
    Smoke test that runs the Module 1 pipeline end-to-end on a tiny dataset.

    This will be expanded with real rule logic later.
    """
    cfg_path = tmp_path / "config.json"
    specs_path = tmp_path / "specs.json"
    csv_path = tmp_path / "readings.csv"
    output_dir = tmp_path / "outputs"

    cfg_path.write_text("{}", encoding="utf-8")
    specs_path.write_text("{}", encoding="utf-8")
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure\n"
        "2026-01-01T00:00:00Z,pump_A,30,2.0,20\n",
        encoding="utf-8",
    )

    classifier.run_module1(
        config_path=cfg_path,
        specs_path=specs_path,
        csv_path=csv_path,
        output_dir=output_dir,
    )

    assert (output_dir / "classifications.jsonl").exists()
    assert (output_dir / "alerts.txt").exists()

