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


# Placeholder for future adapters:
# - load_runtime_csv() for Runtime-based datasets
# - load_row_order_csv() for row-order datasets
