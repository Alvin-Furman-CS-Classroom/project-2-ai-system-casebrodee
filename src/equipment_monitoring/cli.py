"""
Command-line interface for running Module 1.

Example usage (from the project README):

    python -m equipment_monitoring.cli \\
      --config data/module1/config.json \\
      --specs data/module1/equipment_specs.json \\
      --readings data/module1/readings.csv \\
      --output-dir outputs/module1
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .module1 import classifier


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Module 1: Basic Rule-Based Monitoring.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to global threshold configuration JSON.",
    )
    parser.add_argument(
        "--specs",
        required=True,
        help="Path to equipment-specification JSON.",
    )
    parser.add_argument(
        "--readings",
        required=True,
        help="Path to sensor readings CSV.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write Module 1 outputs into.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    classifier.run_module1(
        config_path=Path(args.config),
        specs_path=Path(args.specs),
        csv_path=Path(args.readings),
        output_dir=Path(args.output_dir),
    )


if __name__ == "__main__":
    main()

