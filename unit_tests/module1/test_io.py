from pathlib import Path

from equipment_monitoring.module1 import io


def test_read_and_write_round_trip(tmp_path: Path) -> None:
    """Basic round-trip test for CSV -> JSONL/alerts pipeline helpers."""
    csv_path = tmp_path / "readings.csv"
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure\n"
        "2026-01-01T00:00:00Z,pump_A,30,2.0,20\n",
        encoding="utf-8",
    )

    records = io.read_readings_csv(csv_path)
    assert len(records) == 1

    jsonl_path = tmp_path / "classifications.jsonl"
    alerts_path = tmp_path / "alerts.txt"

    io.write_classifications_jsonl(records, jsonl_path)
    io.write_alerts_text(records, alerts_path)

    assert jsonl_path.exists()
    assert alerts_path.exists()

