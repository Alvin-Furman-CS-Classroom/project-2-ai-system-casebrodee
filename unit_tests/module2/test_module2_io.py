"""Unit tests for Module 2 I/O operations (`io` module).

These tests exercise:
- Loading timestamped CSV files into canonical HistoricalRecord format
- Handling missing timestamp or failure columns
- Proper sorting by machine_id and time_key
"""

import pytest
from pathlib import Path
from datetime import datetime

from equipment_monitoring.module2 import io


def test_load_timestamped_csv_valid(tmp_path: Path) -> None:
    """Test loading a valid timestamped CSV file."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "Machine_ID,Timestamp,Temperature,Pressure,Vibration_Level,Failure_Status\n"
        "MACHINE_001,2025-01-01 00:00:00,56.23,106.0,3.75,0\n"
        "MACHINE_001,2025-01-01 00:10:00,58.45,108.5,4.02,0\n"
        "MACHINE_002,2025-01-01 00:00:00,36.45,179.39,8.02,0\n",
        encoding="utf-8",
    )
    
    records = io.load_timestamped_csv(csv_path)
    
    assert len(records) == 3
    assert records[0].machine_id == "MACHINE_001"
    assert isinstance(records[0].time_key, datetime)
    assert records[0].sensors["Temperature"] == 56.23
    assert records[0].failure_label is False


def test_load_timestamped_csv_with_failure(tmp_path: Path) -> None:
    """Test loading CSV with failure events marked."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "Machine_ID,Timestamp,Temperature,Pressure,Vibration_Level,Failure_Status\n"
        "MACHINE_001,2025-01-01 00:00:00,56.23,106.0,3.75,0\n"
        "MACHINE_001,2025-01-01 00:10:00,58.45,108.5,4.02,1\n",
        encoding="utf-8",
    )
    
    records = io.load_timestamped_csv(csv_path)
    
    assert len(records) == 2
    assert records[0].failure_label is False
    assert records[1].failure_label is True


def test_load_timestamped_csv_missing_timestamp_column(tmp_path: Path) -> None:
    """Test that missing timestamp column raises ValueError."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "Machine_ID,Temperature,Pressure,Failure_Status\n"
        "MACHINE_001,56.23,106.0,0\n",
        encoding="utf-8",
    )
    
    with pytest.raises(ValueError) as exc_info:
        io.load_timestamped_csv(csv_path, timestamp_column="Timestamp")
    
    assert "Timestamp" in str(exc_info.value) or "Missing required columns" in str(exc_info.value)


def test_load_timestamped_csv_missing_failure_column(tmp_path: Path) -> None:
    """Test that missing failure column raises ValueError."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "Machine_ID,Timestamp,Temperature,Pressure\n"
        "MACHINE_001,2025-01-01 00:00:00,56.23,106.0\n",
        encoding="utf-8",
    )
    
    with pytest.raises(ValueError) as exc_info:
        io.load_timestamped_csv(csv_path)
    
    assert "Failure_Status" in str(exc_info.value) or "Missing required columns" in str(exc_info.value)


def test_load_timestamped_csv_sorts_by_time(tmp_path: Path) -> None:
    """Test that records are sorted by machine_id and time_key."""
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "Machine_ID,Timestamp,Temperature,Pressure,Failure_Status\n"
        "MACHINE_001,2025-01-01 00:20:00,58.45,108.5,0\n"
        "MACHINE_001,2025-01-01 00:00:00,56.23,106.0,0\n"
        "MACHINE_001,2025-01-01 00:10:00,57.34,107.2,0\n",
        encoding="utf-8",
    )
    
    records = io.load_timestamped_csv(csv_path)
    
    assert len(records) == 3
    # Should be sorted by time
    assert records[0].time_key < records[1].time_key
    assert records[1].time_key < records[2].time_key


def test_load_timestamped_csv_file_not_found(tmp_path: Path) -> None:
    """Test that missing file raises FileNotFoundError."""
    csv_path = tmp_path / "nonexistent.csv"
    
    with pytest.raises(FileNotFoundError):
        io.load_timestamped_csv(csv_path)


def test_historical_record_comparison() -> None:
    """Test that HistoricalRecord can be compared and sorted."""
    from datetime import datetime
    
    record1 = io.HistoricalRecord(
        machine_id="MACHINE_001",
        time_key=datetime(2025, 1, 1, 0, 0, 0),
        sensors={"Temperature": 50.0},
        failure_label=False
    )
    
    record2 = io.HistoricalRecord(
        machine_id="MACHINE_001",
        time_key=datetime(2025, 1, 1, 0, 10, 0),
        sensors={"Temperature": 55.0},
        failure_label=False
    )
    
    assert record1 < record2
    assert record2 > record1
