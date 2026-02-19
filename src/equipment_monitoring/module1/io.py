"""
I/O helpers for Module 1.

Responsibilities:
- Read sensor readings from CSV into dictionaries.
- Write classification results to JSONL.
- Write human-readable alert text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List
import csv
import json


class CSVValidationError(ValueError):
    """Raised when CSV validation fails."""
    pass


# Required columns for sensor readings CSV
REQUIRED_COLUMNS = {"timestamp", "equipment_id", "temperature", "vibration", "pressure"}


def _validate_csv_columns(columns: List[str]) -> None:
    """
    Validate that the CSV contains all required columns.
    
    Args:
        columns: List of column names from the CSV header.
        
    Raises:
        CSVValidationError: If required columns are missing.
    """
    if not columns:
        raise CSVValidationError("CSV file has no header row (empty or missing columns)")
    
    # Convert to set for easier comparison
    found_columns = set(columns)
    missing_columns = REQUIRED_COLUMNS - found_columns
    
    if missing_columns:
        found_str = ", ".join(sorted(found_columns))
        missing_str = ", ".join(sorted(missing_columns))
        raise CSVValidationError(
            f"CSV file is missing required columns: {missing_str}. "
            f"Found columns: {found_str}"
        )


def read_readings_csv(path: str | Path) -> List[Dict[str, Any]]:
    """
    Read sensor readings CSV into a list of dictionaries.
    
    Validates that the CSV file:
    - Exists and is readable
    - Contains all required columns (timestamp, equipment_id, temperature, vibration, pressure)
    - Is not empty (has at least a header row)
    
    Args:
        path: Path to the CSV file.
        
    Returns:
        List of dictionaries, one per row, with keys matching CSV column names.
        Values are strings as read from CSV (type conversion happens in rules.py).
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
        CSVValidationError: If required columns are missing or file is empty.
        csv.Error: If the CSV file is malformed.
    """
    path = Path(path)
    
    # Check file exists
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    
    # Check file is not empty
    if path.stat().st_size == 0:
        raise CSVValidationError(f"CSV file is empty: {path}")
    
    records: List[Dict[str, Any]] = []
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            # Get column names from the reader
            # DictReader.fieldnames is set after first row is read
            # We need to peek at the first row or read it
            try:
                # Read first row to populate fieldnames
                first_row = next(reader, None)
                if first_row is None:
                    # File has header but no data rows - this is okay, just validate columns
                    if reader.fieldnames is None:
                        raise CSVValidationError(f"CSV file has no header row: {path}")
                    _validate_csv_columns(list(reader.fieldnames))
                    return []  # Empty file with valid header is acceptable
                
                # Validate columns
                if reader.fieldnames is None:
                    raise CSVValidationError(f"CSV file has no header row: {path}")
                _validate_csv_columns(list(reader.fieldnames))
                
                # Add first row back
                records.append(first_row)
                
                # Read remaining rows
                for row in reader:
                    records.append(row)
                    
            except StopIteration:
                # This shouldn't happen if we checked first_row, but handle it
                if reader.fieldnames is None:
                    raise CSVValidationError(f"CSV file has no header row: {path}")
                _validate_csv_columns(list(reader.fieldnames))
                return []
                
    except csv.Error as e:
        raise csv.Error(f"Error reading CSV file {path}: {e}") from e
    
    return records


def write_classifications_jsonl(
    records: Iterable[Dict[str, Any]],
    path: str | Path,
) -> None:
    """
    Write classification records to a JSONL file (one JSON object per line).
    
    Args:
        records: Iterable of classification dictionaries to write.
        path: Path where the JSONL file will be written.
        
    Raises:
        OSError: If the file cannot be written (permissions, disk full, etc.).
    """
    path = Path(path)
    
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
    except OSError as e:
        raise OSError(f"Error writing JSONL file {path}: {e}") from e


def write_alerts_text(
    records: Iterable[Dict[str, Any]],
    path: str | Path,
) -> None:
    """
    Write human-readable alert lines to a text file.
    
    Only writes records with status="anomaly". Normal readings are skipped.
    
    Args:
        records: Iterable of classification dictionaries to process.
        path: Path where the alert text file will be written.
        
    Raises:
        OSError: If the file cannot be written (permissions, disk full, etc.).
    """
    path = Path(path)
    
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(path, "w", encoding="utf-8") as f:
            for record in records:
                if record.get("status") != "anomaly":
                    continue
                ts = record.get("timestamp", "")
                equipment_id = record.get("equipment_id", "")
                violated = record.get("violated_rules") or []
                confidence = record.get("confidence", 0.0)
                violated_str = ", ".join(violated)
                line = (
                    f"[{ts}] {equipment_id} anomaly: {violated_str} "
                    f"(confidence={confidence:.2f})"
                )
                f.write(line + "\n")
    except OSError as e:
        raise OSError(f"Error writing alert file {path}: {e}") from e

