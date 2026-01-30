import pytest
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


def test_read_readings_csv_valid(tmp_path: Path) -> None:
    """Test reading a valid CSV file with all required columns."""
    csv_path = tmp_path / "readings.csv"
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure\n"
        "2026-01-01T00:00:00Z,pump_A,30.0,2.1,20.0\n"
        "2026-01-01T00:01:00Z,pump_B,25.0,1.5,15.0\n",
        encoding="utf-8",
    )

    records = io.read_readings_csv(csv_path)

    assert len(records) == 2
    assert records[0]["timestamp"] == "2026-01-01T00:00:00Z"
    assert records[0]["equipment_id"] == "pump_A"
    assert records[0]["temperature"] == "30.0"


def test_read_readings_csv_with_extra_columns(tmp_path: Path) -> None:
    """Test that CSV with extra columns (beyond required) is acceptable."""
    csv_path = tmp_path / "readings.csv"
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure,extra_column\n"
        "2026-01-01T00:00:00Z,pump_A,30.0,2.1,20.0,extra_value\n",
        encoding="utf-8",
    )

    records = io.read_readings_csv(csv_path)

    assert len(records) == 1
    assert "extra_column" in records[0]
    assert records[0]["extra_column"] == "extra_value"


def test_read_readings_csv_missing_column(tmp_path: Path) -> None:
    """Test that missing required column raises CSVValidationError."""
    csv_path = tmp_path / "readings.csv"
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration\n"  # Missing 'pressure'
        "2026-01-01T00:00:00Z,pump_A,30.0,2.1\n",
        encoding="utf-8",
    )

    with pytest.raises(io.CSVValidationError) as exc_info:
        io.read_readings_csv(csv_path)

    assert "pressure" in str(exc_info.value).lower()
    assert "missing" in str(exc_info.value).lower()


def test_read_readings_csv_multiple_missing_columns(tmp_path: Path) -> None:
    """Test that multiple missing columns are all reported."""
    csv_path = tmp_path / "readings.csv"
    csv_path.write_text(
        "timestamp,equipment_id,temperature\n"  # Missing 'vibration' and 'pressure'
        "2026-01-01T00:00:00Z,pump_A,30.0\n",
        encoding="utf-8",
    )

    with pytest.raises(io.CSVValidationError) as exc_info:
        io.read_readings_csv(csv_path)

    error_msg = str(exc_info.value).lower()
    assert "vibration" in error_msg
    assert "pressure" in error_msg


def test_read_readings_csv_empty_file(tmp_path: Path) -> None:
    """Test that empty CSV file raises CSVValidationError."""
    csv_path = tmp_path / "readings.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(io.CSVValidationError) as exc_info:
        io.read_readings_csv(csv_path)

    assert "empty" in str(exc_info.value).lower()


def test_read_readings_csv_header_only(tmp_path: Path) -> None:
    """Test that CSV with only header (no data rows) is acceptable."""
    csv_path = tmp_path / "readings.csv"
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure\n",
        encoding="utf-8",
    )

    records = io.read_readings_csv(csv_path)

    assert len(records) == 0  # No data rows, but valid header


def test_read_readings_csv_file_not_found(tmp_path: Path) -> None:
    """Test that missing file raises FileNotFoundError."""
    csv_path = tmp_path / "nonexistent.csv"

    with pytest.raises(FileNotFoundError):
        io.read_readings_csv(csv_path)


def test_read_readings_csv_wrong_column_order(tmp_path: Path) -> None:
    """Test that column order doesn't matter, only presence."""
    csv_path = tmp_path / "readings.csv"
    csv_path.write_text(
        "pressure,vibration,temperature,equipment_id,timestamp\n"  # Different order
        "20.0,2.1,30.0,pump_A,2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )

    records = io.read_readings_csv(csv_path)

    assert len(records) == 1
    assert records[0]["temperature"] == "30.0"
    assert records[0]["pressure"] == "20.0"


def test_write_classifications_jsonl_creates_directory(tmp_path: Path) -> None:
    """Test that write_classifications_jsonl creates parent directory if needed."""
    output_dir = tmp_path / "nested" / "outputs"
    jsonl_path = output_dir / "classifications.jsonl"
    
    records = [{"timestamp": "2026-01-01T00:00:00Z", "status": "normal"}]
    
    io.write_classifications_jsonl(records, jsonl_path)
    
    assert jsonl_path.exists()
    assert output_dir.exists()


def test_write_alerts_text_only_anomalies(tmp_path: Path) -> None:
    """Test that write_alerts_text only writes anomaly records."""
    alerts_path = tmp_path / "alerts.txt"
    
    records = [
        {"status": "normal", "timestamp": "2026-01-01T00:00:00Z"},
        {"status": "anomaly", "timestamp": "2026-01-01T00:01:00Z", "equipment_id": "pump_A", "violated_rules": ["temperature_high"], "confidence": 0.7},
        {"status": "normal", "timestamp": "2026-01-01T00:02:00Z"},
        {"status": "anomaly", "timestamp": "2026-01-01T00:03:00Z", "equipment_id": "pump_B", "violated_rules": ["pressure_low"], "confidence": 0.8},
    ]
    
    io.write_alerts_text(records, alerts_path)
    
    content = alerts_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    
    assert len(lines) == 2  # Only 2 anomalies
    assert "pump_A" in content
    assert "pump_B" in content
    assert "temperature_high" in content
    assert "pressure_low" in content

