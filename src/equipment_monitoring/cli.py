"""
Command-line interface for running modules.

Example usage:

Module 1:
    python -m equipment_monitoring.cli --module 1 \\
      --config data/module1/config.json \\
      --specs data/module1/equipment_specs.json \\
      --readings data/module1/readings.csv \\
      --output-dir outputs/module1

Module 2:
    python -m equipment_monitoring.cli --module 2 \\
      --data src/data/machine_failure_data_timestamp.csv \\
      --graph-config src/data/module2/graph_config.json \\
      --search-params src/data/module2/search_params.json \\
      --output-dir outputs/module2
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
        description="Run equipment monitoring modules.",
    )
    parser.add_argument(
        "--module",
        type=int,
        choices=[1, 2],
        required=True,
        help="Module number to run (1 or 2).",
    )
    
    # Module 1 arguments
    parser.add_argument(
        "--config",
        help="Path to global threshold configuration JSON (Module 1).",
    )
    parser.add_argument(
        "--specs",
        help="Path to equipment-specification JSON (Module 1).",
    )
    parser.add_argument(
        "--readings",
        help="Path to sensor readings CSV (Module 1).",
    )
    
    # Module 2 arguments
    parser.add_argument(
        "--data",
        help="Path to historical sensor data CSV (Module 2).",
    )
    parser.add_argument(
        "--graph-config",
        help="Path to graph configuration JSON (Module 2).",
    )
    parser.add_argument(
        "--search-params",
        help="Path to search parameters JSON (Module 2).",
    )
    
    # Common argument
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write outputs into.",
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

