"""
I/O operations for Module 2: Loading and normalizing historical sensor data.

This module defines the canonical "historical record" format that all data sources
are normalized to, regardless of whether they use timestamps, runtime, or row order.
"""

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union


@dataclass
class HistoricalRecord:
    """
    Canonical format for a historical sensor reading with failure information.
    
    This format is used internally by Module 2 regardless of the source data format.
    All CSV adapters (timestamp-based, runtime-based, row-order) convert their
    data into this structure.
    
    Attributes:
        machine_id: Unique identifier for the equipment/machine
        time_key: Temporal ordering key - can be:
                  - datetime object (for timestamp-based data)
                  - float (for runtime-based data, e.g., cumulative hours)
                  - int (for row-order data, sequence number)
        sensors: Dictionary of sensor name -> numeric value
                 Common keys: 'temperature', 'vibration', 'pressure', etc.
        failure_label: Boolean indicating if this reading corresponds to a failure event
                      (True = failure occurred, False = normal operation)
    """
    machine_id: str
    time_key: Union[datetime, float, int]
    sensors: Dict[str, float]
    failure_label: bool
    
    def __lt__(self, other: 'HistoricalRecord') -> bool:
        """Enable sorting by time_key."""
        if isinstance(self.time_key, datetime) and isinstance(other.time_key, datetime):
            return self.time_key < other.time_key
        elif isinstance(self.time_key, (int, float)) and isinstance(other.time_key, (int, float)):
            return self.time_key < other.time_key
        else:
            # Mixed types: convert datetime to timestamp for comparison
            self_val = self.time_key.timestamp() if isinstance(self.time_key, datetime) else self.time_key
            other_val = other.time_key.timestamp() if isinstance(other.time_key, datetime) else other.time_key
            return self_val < other_val


TRUE_VALUES = {"1", "true", "yes"}
TIMESTAMP_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S")


def _ensure_csv_exists(csv_path: Union[str, Path]) -> Path:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    return path


def _validate_required_columns(fieldnames: Iterable[str] | None, required: Iterable[str], *, label: str) -> List[str]:
    if fieldnames is None:
        raise ValueError("CSV has no header row")
    found = list(fieldnames)
    missing = [col for col in required if col not in found]
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")
    return found


def _parse_timestamp(timestamp_str: str) -> datetime:
    cleaned = timestamp_str.strip()
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        for fmt in TIMESTAMP_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
    raise ValueError(f"Could not parse timestamp: {cleaned}")


def _parse_failure_label(value: object) -> bool:
    return str(value).strip().lower() in TRUE_VALUES


def _extract_numeric_sensors(
    row: Dict[str, object],
    sensor_columns: Iterable[str],
    *,
    rename: Optional[Dict[str, str]] = None,
) -> Dict[str, float]:
    sensors: Dict[str, float] = {}
    for sensor_col in sensor_columns:
        if sensor_col not in row:
            continue
        try:
            output_key = rename.get(sensor_col, sensor_col) if rename else sensor_col
            sensors[output_key] = float(row[sensor_col])
        except (ValueError, TypeError):
            continue
    return sensors


def _sort_records(records: List["HistoricalRecord"]) -> List["HistoricalRecord"]:
    records.sort(key=lambda r: (r.machine_id, r.time_key))
    return records


def load_timestamped_csv(
    csv_path: Union[str, Path],
    timestamp_column: str = "Timestamp",
    machine_id_column: str = "Machine_ID",
    failure_column: str = "Failure_Status",
    sensor_columns: Optional[List[str]] = None
) -> List[HistoricalRecord]:
    """
    Load a timestamped CSV file and convert to canonical HistoricalRecord format.
    
    This is the primary adapter for timestamp-based datasets like
    machine_failure_data_timestamp.csv.
    
    Args:
        csv_path: Path to the CSV file
        timestamp_column: Name of the timestamp column (default: "Timestamp")
        machine_id_column: Name of the machine ID column (default: "Machine_ID")
        failure_column: Name of the failure status column (default: "Failure_Status")
        sensor_columns: List of sensor column names to include. If None, auto-detect
                       by excluding timestamp, machine_id, and failure columns.
    
    Returns:
        List of HistoricalRecord objects, sorted by time_key within each machine
    
    Raises:
        FileNotFoundError: If csv_path doesn't exist
        ValueError: If required columns are missing
    """
    csv_path = _ensure_csv_exists(csv_path)
    
    records = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = _validate_required_columns(
            reader.fieldnames,
            [timestamp_column, machine_id_column, failure_column],
            label="Missing required columns",
        )

        # Auto-detect sensor columns if not provided
        if sensor_columns is None:
            sensor_columns = [
                col for col in fieldnames
                if col not in [timestamp_column, machine_id_column, failure_column]
            ]
        
        for row in reader:
            timestamp = _parse_timestamp(str(row[timestamp_column]))
            machine_id = str(row[machine_id_column]).strip()
            failure_label = _parse_failure_label(row[failure_column])
            sensors = _extract_numeric_sensors(row, sensor_columns)
            records.append(HistoricalRecord(
                machine_id=machine_id,
                time_key=timestamp,
                sensors=sensors,
                failure_label=failure_label
            ))
    return _sort_records(records)


# Column name mapping from Module 1 schema to Module 2 graph sensor names
MODULE1_TO_GRAPH_SENSORS = {
    "temperature": "Temperature",
    "vibration": "Vibration_Level",
    "pressure": "Pressure",
}


def load_module1_schema_csv(
    csv_path: Union[str, Path],
    failure_column: str = "failure_status",
) -> List[HistoricalRecord]:
    """
    Load a CSV that uses Module 1's column schema (timestamp, equipment_id, temperature,
    vibration, pressure) with an optional failure_status column for ground-truth labels.

    This allows the same dataset to be used by both Module 1 (rule-based classification)
    and Module 2 (failure pattern discovery), satisfying the "Module 2 depends on Module 1"
    integration: one pipeline runs Module 1 on this CSV, then Module 2 uses the same CSV
    plus optional Module 1 classifications.

    Args:
        csv_path: Path to the CSV file.
        failure_column: Name of the failure status column (default: "failure_status").
                        If missing, all records are treated as non-failure.

    Returns:
        List of HistoricalRecord objects. Sensor dict uses graph-style keys
        (Temperature, Vibration_Level, Pressure) so graph building works unchanged.

    Raises:
        FileNotFoundError: If csv_path doesn't exist.
        ValueError: If required columns (timestamp, equipment_id, temperature, vibration, pressure) are missing.
    """
    csv_path = _ensure_csv_exists(csv_path)

    required = {"timestamp", "equipment_id", "temperature", "vibration", "pressure"}
    records = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        found = set(_validate_required_columns(reader.fieldnames, required, label="Module 1 schema CSV"))

        has_failure = failure_column in found

        for row in reader:
            ts = _parse_timestamp(str(row["timestamp"]))
            machine_id = str(row["equipment_id"]).strip()
            failure_label = _parse_failure_label(row[failure_column]) if has_failure else False
            sensors = _extract_numeric_sensors(
                row,
                MODULE1_TO_GRAPH_SENSORS.keys(),
                rename=MODULE1_TO_GRAPH_SENSORS,
            )

            records.append(
                HistoricalRecord(
                    machine_id=machine_id,
                    time_key=ts,
                    sensors=sensors,
                    failure_label=failure_label,
                )
            )

    return _sort_records(records)


def load_classifications_jsonl(
    jsonl_path: Union[str, Path],
) -> set:
    """
    Load Module 1 classifications.jsonl and return the set of (equipment_id, timestamp)
    for rows classified as anomaly. Used by Module 2 to enrich warning signs with
    Module 1 overlap (e.g. how often a pattern coincided with rule-based anomalies).

    Args:
        jsonl_path: Path to classifications.jsonl from Module 1.

    Returns:
        Set of (equipment_id, timestamp_str) for records with status == "anomaly".
        Timestamps are normalized to ISO-style strings for matching.
    """
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Classifications file not found: {jsonl_path}")

    anomaly_set = set()
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("status") != "anomaly":
                continue
            eid = rec.get("equipment_id", "")
            ts = rec.get("timestamp", "")
            if eid is not None and ts is not None:
                anomaly_set.add((str(eid), str(ts)))
    return anomaly_set


def load_classification_anomaly_rates(
    jsonl_path: Union[str, Path],
) -> Dict[str, float]:
    """
    Load Module 1 classifications and compute anomaly rate per equipment.

    Args:
        jsonl_path: Path to classifications.jsonl from Module 1.

    Returns:
        Mapping of equipment_id -> anomaly_rate in [0, 1].
    """
    jsonl_path = Path(jsonl_path)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Classifications file not found: {jsonl_path}")

    totals: Dict[str, int] = {}
    anomalies: Dict[str, int] = {}
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            equipment_id = str(rec.get("equipment_id", ""))
            if not equipment_id:
                continue
            totals[equipment_id] = totals.get(equipment_id, 0) + 1
            if rec.get("status") == "anomaly":
                anomalies[equipment_id] = anomalies.get(equipment_id, 0) + 1

    return {
        equipment_id: (anomalies.get(equipment_id, 0) / total)
        for equipment_id, total in totals.items()
        if total > 0
    }
