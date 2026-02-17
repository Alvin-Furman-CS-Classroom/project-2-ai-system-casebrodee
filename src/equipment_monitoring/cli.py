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
import json
import sys
import traceback
from pathlib import Path

from .module1 import classifier
from .module1 import config as config_module
from .module1 import io as io_module


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
    try:
        classifier.run_module1(
            config_path=Path(args.config),
            specs_path=Path(args.specs),
            csv_path=Path(args.readings),
            output_dir=Path(args.output_dir),
        )
    except FileNotFoundError as e:
        print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)
    except config_module.ConfigValidationError as e:
        print(f"[config error] {e}", file=sys.stderr)
        sys.exit(1)
    except io_module.CSVValidationError as e:
        print(f"[csv error] {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[json error] {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"[io error] {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        print(f"[unexpected error] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

