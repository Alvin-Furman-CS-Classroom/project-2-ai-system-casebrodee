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
    cd <Path to project root>
    PYTHONPATH=src python3 -m equipment_monitoring.cli --module 2 --data src/data/machine_failure_data_timestamp.csv --graph-config src/data/module2/graph_config.json --search-params src/data/module2/search_params.json --output-dir outputs/module2

Module 3 (after Module 1 + 2 on the same dataset):
    PYTHONPATH=src python3 -m equipment_monitoring.cli --module 3 \\
      --kb src/data/module3/kb.json \\
      --classifications outputs/module1/classifications.jsonl \\
      --sequences outputs/module2/sequences.json \\
      --warning-signs outputs/module2/warning_signs.json \\
      --output-dir outputs/module3

Module 4 (after Module 3):
    PYTHONPATH=src python3 -m equipment_monitoring.cli --module 4 \\
      --diagnosis outputs/module3/diagnosis.json \\
      --production-schedule src/data/module4/production_schedule.json \\
      --output-dir outputs/module4

Module 6 (after Module 3; Module 5 optional):
    PYTHONPATH=src python3 -m equipment_monitoring.cli --module 6 \\
      --diagnosis outputs/module3/diagnosis.json \\
      --output-dir outputs/module6
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path

from .module1 import classifier
from .module1 import config as config_module
from .module1 import io as io_module
from .module2 import runner as module2_runner
from .module3 import runner as module3_runner
from .module3.kb_loader import KnowledgeBaseError
from .module4 import runner as module4_runner
from .module4.loader import Module4ConfigError
from .module6 import runner as module6_runner
from .module6.loader import Module6ConfigError
from . import reporting

_UNHANDLED = "__unhandled__"

HandlerRow = tuple[type[BaseException], str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run equipment monitoring modules.",
    )
    parser.add_argument(
        "--module",
        type=int,
        choices=[1, 2, 3, 4, 6],
        required=True,
        help="Module number to run (1–4, 6).",
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
    parser.add_argument(
        "--data-format",
        choices=["timestamped", "module1"],
        default="timestamped",
        help="CSV format: 'timestamped' (Machine_ID, Timestamp, Failure_Status) or 'module1' (timestamp, equipment_id, temperature, vibration, pressure, failure_status). Default: timestamped.",
    )
    parser.add_argument(
        "--classifications",
        help="Path to Module 1 classifications.jsonl (Module 2/6). Module 2: anomaly rate in warning signs. Module 6: optional override for risk×M1-hot start states.",
    )

    # Module 3 arguments
    parser.add_argument(
        "--kb",
        help="Path to Module 3 knowledge base JSON (rules).",
    )
    parser.add_argument(
        "--sequences",
        help="Path to Module 2 sequences.json (required for Module 3).",
    )
    parser.add_argument(
        "--warning-signs",
        help="Path to Module 2 warning_signs.json (required for Module 3).",
    )

    # Module 4 arguments
    parser.add_argument(
        "--diagnosis",
        help="Path to Module 3 diagnosis.json (required for Module 4 and Module 6).",
    )
    parser.add_argument(
        "--module4-config",
        help="Path to Module 4 maintenance optimization JSON (default: src/data/module4/module4_config.json).",
    )
    parser.add_argument(
        "--production-schedule",
        help="Optional JSON: label/notes and max_total_downtime_hours cap (min with base config).",
    )

    # Module 6 arguments
    parser.add_argument(
        "--module6-config",
        help="Path to Module 6 JSON (default: src/data/module6/module6_config.json).",
    )
    parser.add_argument(
        "--mdp",
        help="Override MDP JSON path (default: mdp_path inside Module 6 config).",
    )

    # Common argument
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write outputs into.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate/update static HTML report from outputs after module run.",
    )
    parser.add_argument(
        "--report-path",
        help="Optional explicit path for generated HTML report.",
    )
    parser.add_argument(
        "--fleet-summary",
        action="store_true",
        help="After a successful module run, write fleet_summary.json under the inferred outputs root (same root as --report).",
    )

    return parser.parse_args(argv)


def _try_run_module(run: Callable[[], None], handlers: Sequence[HandlerRow]) -> None:
    """Run ``run()``; map domain exceptions to stderr messages and ``sys.exit(1)``."""
    try:
        run()
    except Exception as e:
        for exc_type, tag in handlers:
            if isinstance(e, exc_type):
                if tag == _UNHANDLED:
                    traceback.print_exc(file=sys.stderr)
                    print(f"[unexpected error] {e}", file=sys.stderr)
                    sys.exit(1)
                print(f"[{tag}] {e}", file=sys.stderr)
                sys.exit(1)
        raise


def _maybe_write_fleet_summary(args: argparse.Namespace) -> None:
    if not args.fleet_summary:
        return
    out_dir = Path(args.output_dir)
    root = reporting.infer_outputs_root(out_dir, args.module)
    path = reporting.write_fleet_summary(root)
    print(f"Fleet summary wrote {path}")


def _after_successful_run(args: argparse.Namespace, report_path: Path | None) -> None:
    """Regenerate HTML report and/or fleet JSON when flags are set."""
    if args.report:
        out = reporting.generate_report_from_run(
            output_dir=Path(args.output_dir),
            module_number=args.module,
            report_path=report_path,
        )
        print(f"Report wrote {out}")
    _maybe_write_fleet_summary(args)


def _handlers_module1() -> tuple[HandlerRow, ...]:
    return (
        (FileNotFoundError, "error"),
        (config_module.ConfigValidationError, "config error"),
        (io_module.CSVValidationError, "csv error"),
        (json.JSONDecodeError, "json error"),
        (OSError, "io error"),
        (Exception, _UNHANDLED),
    )


def _handlers_module2() -> tuple[HandlerRow, ...]:
    return (
        (FileNotFoundError, "error"),
        (json.JSONDecodeError, "json error"),
        (ValueError, "value error"),
        (KeyError, "error"),
        (OSError, "io error"),
        (Exception, _UNHANDLED),
    )


def _handlers_module3() -> tuple[HandlerRow, ...]:
    return (
        (FileNotFoundError, "error"),
        (KnowledgeBaseError, "kb error"),
        (json.JSONDecodeError, "json error"),
        (OSError, "io error"),
        (Exception, _UNHANDLED),
    )


def _handlers_module4() -> tuple[HandlerRow, ...]:
    return (
        (FileNotFoundError, "error"),
        (Module4ConfigError, "module4 config error"),
        (json.JSONDecodeError, "json error"),
        (ValueError, "value error"),
        (OSError, "io error"),
        (Exception, _UNHANDLED),
    )


def _handlers_module6() -> tuple[HandlerRow, ...]:
    return (
        (FileNotFoundError, "error"),
        (Module6ConfigError, "module6 error"),
        (json.JSONDecodeError, "json error"),
        (ValueError, "value error"),
        (OSError, "io error"),
        (Exception, _UNHANDLED),
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    report_path = Path(args.report_path) if args.report_path else None

    if args.module == 1:
        if not args.config or not args.specs or not args.readings:
            print("[error] Module 1 requires --config, --specs, and --readings", file=sys.stderr)
            sys.exit(1)

        def run_m1() -> None:
            classifier.run_module1(
                config_path=Path(args.config),
                specs_path=Path(args.specs),
                csv_path=Path(args.readings),
                output_dir=Path(args.output_dir),
            )

        _try_run_module(run_m1, _handlers_module1())
        _after_successful_run(args, report_path)

    elif args.module == 2:
        if not args.data or not args.graph_config or not args.search_params:
            print("[error] Module 2 requires --data, --graph-config, and --search-params", file=sys.stderr)
            sys.exit(1)

        def run_m2() -> None:
            classifications_path = Path(args.classifications) if args.classifications else None
            module2_runner.run_module2(
                data_path=Path(args.data),
                graph_config_path=Path(args.graph_config),
                search_params_path=Path(args.search_params),
                output_dir=Path(args.output_dir),
                data_format=args.data_format,
                classifications_path=classifications_path,
            )

        _try_run_module(run_m2, _handlers_module2())
        _after_successful_run(args, report_path)

    elif args.module == 3:
        if not args.kb or not args.classifications or not args.sequences or not args.warning_signs:
            print(
                "[error] Module 3 requires --kb, --classifications, --sequences, and --warning-signs",
                file=sys.stderr,
            )
            sys.exit(1)

        def run_m3() -> None:
            module3_runner.run_module3(
                kb_path=Path(args.kb),
                classifications_path=Path(args.classifications),
                sequences_path=Path(args.sequences),
                warning_signs_path=Path(args.warning_signs),
                output_dir=Path(args.output_dir),
            )

        _try_run_module(run_m3, _handlers_module3())
        _after_successful_run(args, report_path)

    elif args.module == 4:
        if not args.diagnosis:
            print("[error] Module 4 requires --diagnosis", file=sys.stderr)
            sys.exit(1)
        repo_default = Path(__file__).resolve().parent.parent / "data" / "module4" / "module4_config.json"
        config_path = Path(args.module4_config) if args.module4_config else repo_default

        def run_m4() -> None:
            prod_path = Path(args.production_schedule) if args.production_schedule else None
            module4_runner.run_module4(
                diagnosis_path=Path(args.diagnosis),
                config_path=config_path,
                output_dir=Path(args.output_dir),
                production_schedule_path=prod_path,
            )

        _try_run_module(run_m4, _handlers_module4())
        _after_successful_run(args, report_path)

    elif args.module == 6:
        if not args.diagnosis:
            print("[error] Module 6 requires --diagnosis", file=sys.stderr)
            sys.exit(1)
        repo_default_m6 = Path(__file__).resolve().parent.parent / "data" / "module6" / "module6_config.json"
        m6_cfg = Path(args.module6_config) if args.module6_config else repo_default_m6

        def run_m6() -> None:
            mdp_override = Path(args.mdp) if args.mdp else None
            m4_override = Path(args.module4_config) if args.module4_config else None
            cls_m6 = Path(args.classifications) if args.classifications else None
            module6_runner.run_module6(
                diagnosis_path=Path(args.diagnosis),
                module6_config_path=m6_cfg,
                output_dir=Path(args.output_dir),
                mdp_path=mdp_override,
                module4_config_path=m4_override,
                classifications_path=cls_m6,
            )

        _try_run_module(run_m6, _handlers_module6())
        _after_successful_run(args, report_path)


if __name__ == "__main__":
    main()
