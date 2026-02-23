"""
I/O operations for Module 2: Loading and normalizing historical sensor data.

This module defines the canonical "historical record" format that all data sources
are normalized to, regardless of whether they use timestamps, runtime, or row order.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union
import csv
from pathlib import Path


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
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    records = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Auto-detect sensor columns if not provided
        if sensor_columns is None:
            sensor_columns = [
                col for col in reader.fieldnames
                if col not in [timestamp_column, machine_id_column, failure_column]
            ]
        
        # Validate required columns exist
        required = [timestamp_column, machine_id_column, failure_column]
        missing = [col for col in required if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        for row in reader:
            # Parse timestamp
            timestamp_str = row[timestamp_column].strip()
            try:
                # Try ISO format first
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except ValueError:
                # Try common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        timestamp = datetime.strptime(timestamp_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"Could not parse timestamp: {timestamp_str}")
            
            # Parse machine ID
            machine_id = row[machine_id_column].strip()
            
            # Parse failure label (handle both 0/1 and True/False)
            failure_str = str(row[failure_column]).strip().lower()
            failure_label = failure_str in ['1', 'true', 'yes']
            
            # Extract sensor values
            sensors = {}
            for sensor_col in sensor_columns:
                if sensor_col in row:
                    try:
                        sensors[sensor_col] = float(row[sensor_col])
                    except (ValueError, TypeError):
                        # Skip invalid sensor values
                        continue
            
            records.append(HistoricalRecord(
                machine_id=machine_id,
                time_key=timestamp,
                sensors=sensors,
                failure_label=failure_label
            ))
    
    # Sort by machine_id, then by time_key
    records.sort(key=lambda r: (r.machine_id, r.time_key))
    
    return records


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
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    required = {"timestamp", "equipment_id", "temperature", "vibration", "pressure"}
    records = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")
        found = set(reader.fieldnames)
        missing = required - found
        if missing:
            raise ValueError(f"Module 1 schema CSV missing columns: {missing}")

        has_failure = failure_column in found

        for row in reader:
            ts_str = row["timestamp"].strip()
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        ts = datetime.strptime(ts_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"Could not parse timestamp: {ts_str}")

            machine_id = row["equipment_id"].strip()
            failure_label = False
            if has_failure:
                failure_str = str(row[failure_column]).strip().lower()
                failure_label = failure_str in ["1", "true", "yes"]

            sensors = {}
            for m1_key, graph_key in MODULE1_TO_GRAPH_SENSORS.items():
                if m1_key in row:
                    try:
                        sensors[graph_key] = float(row[m1_key])
                    except (ValueError, TypeError):
                        continue

            records.append(
                HistoricalRecord(
                    machine_id=machine_id,
                    time_key=ts,
                    sensors=sensors,
                    failure_label=failure_label,
                )
            )

    records.sort(key=lambda r: (r.machine_id, r.time_key))
    return records


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
    import json
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
