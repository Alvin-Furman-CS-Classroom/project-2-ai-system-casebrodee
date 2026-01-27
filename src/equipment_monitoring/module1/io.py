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


def read_readings_csv(path: str | Path) -> List[Dict[str, Any]]:
    """Read sensor readings CSV into a list of dictionaries."""
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def write_classifications_jsonl(
    records: Iterable[Dict[str, Any]],
    path: str | Path,
) -> None:
    """Write classification records to a JSONL file (one JSON object per line)."""
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def write_alerts_text(
    records: Iterable[Dict[str, Any]],
    path: str | Path,
) -> None:
    """Write human-readable alert lines to a text file."""
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

