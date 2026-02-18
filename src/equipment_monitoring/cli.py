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
import sys
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
    
    if args.module == 1:
        # Validate Module 1 arguments
        if not args.config or not args.specs or not args.readings:
            print("[error] Module 1 requires --config, --specs, and --readings", file=sys.stderr)
            sys.exit(1)
        
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
        except Exception as e:
            print(f"[unexpected error] {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.module == 2:
        # Validate Module 2 arguments
        if not args.data or not args.graph_config or not args.search_params:
            print("[error] Module 2 requires --data, --graph-config, and --search-params", file=sys.stderr)
            sys.exit(1)
        
        try:
            from .module2 import runner
            runner.run_module2(
                data_path=Path(args.data),
                graph_config_path=Path(args.graph_config),
                search_params_path=Path(args.search_params),
                output_dir=Path(args.output_dir),
            )
        except FileNotFoundError as e:
            print(f"[error] {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"[unexpected error] {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

