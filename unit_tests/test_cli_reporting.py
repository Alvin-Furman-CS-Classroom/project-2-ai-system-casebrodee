"""CLI tests for report argument parsing and invocation."""

from __future__ import annotations

from pathlib import Path

from equipment_monitoring import cli


def test_parse_args_includes_report_flags() -> None:
    args = cli.parse_args(
        [
            "--module",
            "1",
            "--config",
            "config.json",
            "--specs",
            "specs.json",
            "--readings",
            "readings.csv",
            "--output-dir",
            "outputs/module1",
            "--report",
            "--report-path",
            "outputs/custom_report.html",
        ]
    )
    assert args.report is True
    assert args.report_path == "outputs/custom_report.html"


def test_main_module1_triggers_report(monkeypatch, tmp_path: Path) -> None:
    called = {"module1": False, "report": False}

    def fake_run_module1(*, config_path, specs_path, csv_path, output_dir):
        called["module1"] = True
        assert config_path == tmp_path / "config.json"
        assert specs_path == tmp_path / "specs.json"
        assert csv_path == tmp_path / "readings.csv"
        assert output_dir == tmp_path / "outputs" / "module1"

    def fake_report(*, output_dir, module_number, report_path):
        called["report"] = True
        assert output_dir == tmp_path / "outputs" / "module1"
        assert module_number == 1
        assert report_path == tmp_path / "outputs" / "report.html"
        return report_path

    monkeypatch.setattr(cli.classifier, "run_module1", fake_run_module1)
    monkeypatch.setattr(cli.reporting, "generate_report_from_run", fake_report)

    cli.main(
        [
            "--module",
            "1",
            "--config",
            str(tmp_path / "config.json"),
            "--specs",
            str(tmp_path / "specs.json"),
            "--readings",
            str(tmp_path / "readings.csv"),
            "--output-dir",
            str(tmp_path / "outputs" / "module1"),
            "--report",
            "--report-path",
            str(tmp_path / "outputs" / "report.html"),
        ]
    )

    assert called["module1"] is True
    assert called["report"] is True
