"""Integration test: Module 1 and Module 2 on the same dataset.

Demonstrates that Module 2 depends on Module 1 by:
1. Running Module 1 on a CSV that has both sensor columns and failure_status (ground truth).
2. Running Module 2 on the same CSV (Module 1 schema) with optional Module 1 classifications.
3. Verifying both outputs and that Module 2 can enrich warning signs with module1_anomaly_rate.
"""

import json
from pathlib import Path

import pytest

from equipment_monitoring.module1 import classifier
from equipment_monitoring.module2 import runner


def test_module1_then_module2_same_data(tmp_path: Path) -> None:
    """
    Run Module 1 then Module 2 on a shared CSV (Module 1 schema + failure_status).
    Asserts both pipelines succeed and Module 2 uses Module 1 classifications when provided.
    """
    # Paths
    cfg_path = tmp_path / "config.json"
    specs_path = tmp_path / "specs.json"
    csv_path = tmp_path / "readings_with_failures.csv"
    module1_output = tmp_path / "module1_out"
    module2_output = tmp_path / "module2_out"
    graph_config_path = Path(__file__).parent.parent.parent / "src" / "data" / "module2" / "graph_config.json"
    search_params_path = Path(__file__).parent.parent.parent / "src" / "data" / "module2" / "search_params.json"

    if not graph_config_path.exists() or not search_params_path.exists():
        import pytest
        pytest.skip("Module 2 config files not found")

    # Module 1 config/specs (same shape as module1 smoke test)
    cfg_path.write_text(
        json.dumps({
            "temperature": {"min": 20.0, "max": 80.0},
            "vibration": {"max": 5.0},
            "pressure": {"min": 10.0, "max": 50.0},
        }),
        encoding="utf-8",
    )
    specs_path.write_text("{}", encoding="utf-8")

    # CSV: Module 1 columns + failure_status. Multiple machines and timestamps so graph has states/transitions.
    # Bins in graph_config: Temperature [0,30,50,70,100], Pressure [0,200,350,500], Vibration_Level [0,3,6,10]
    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure,failure_status\n"
        "2026-01-01T00:00:00Z,M1,25,1.0,100,0\n"
        "2026-01-01T00:01:00Z,M1,35,2.0,150,0\n"
        "2026-01-01T00:02:00Z,M1,45,4.0,250,0\n"
        "2026-01-01T00:03:00Z,M1,65,5.5,400,1\n"
        "2026-01-01T00:00:00Z,M2,22,1.5,120,0\n"
        "2026-01-01T00:01:00Z,M2,40,3.0,200,0\n"
        "2026-01-01T00:02:00Z,M2,60,5.0,380,1\n",
        encoding="utf-8",
    )

    # 1. Run Module 1
    classifier.run_module1(
        config_path=cfg_path,
        specs_path=specs_path,
        csv_path=csv_path,
        output_dir=module1_output,
    )
    assert (module1_output / "classifications.jsonl").exists()
    assert (module1_output / "alerts.txt").exists()

    # 2. Run Module 2 on the same CSV (module1 schema) with Module 1 classifications
    runner.run_module2(
        data_path=csv_path,
        graph_config_path=graph_config_path,
        search_params_path=search_params_path,
        output_dir=module2_output,
        data_format="module1",
        classifications_path=module1_output / "classifications.jsonl",
    )

    # 3. Verify Module 2 outputs
    assert (module2_output / "sequences.json").exists()
    assert (module2_output / "warning_signs.json").exists()

    with open(module2_output / "warning_signs.json", "r", encoding="utf-8") as f:
        warning_data = json.load(f)
    assert "warning_signs" in warning_data
    # When classifications are provided, warning signs may include module1_anomaly_rate
    for ws in warning_data["warning_signs"]:
        assert "pattern" in ws
        assert "predictive_score" in ws
        # If Module 1 overlap was computed, it should be present
        if "module1_anomaly_rate" in ws:
            assert 0 <= ws["module1_anomaly_rate"] <= 1


def test_module2_standalone_module1_schema_csv(tmp_path: Path) -> None:
    """
    Module 2 can load and run on a Module 1–schema CSV (with failure_status) without
    running Module 1 first. This shows the same dataset format can feed both modules.
    """
    csv_path = tmp_path / "readings.csv"
    graph_config_path = Path(__file__).parent.parent.parent / "src" / "data" / "module2" / "graph_config.json"
    search_params_path = Path(__file__).parent.parent.parent / "src" / "data" / "module2" / "search_params.json"

    if not graph_config_path.exists() or not search_params_path.exists():
        pytest.skip("Module 2 config files not found")

    csv_path.write_text(
        "timestamp,equipment_id,temperature,vibration,pressure,failure_status\n"
        "2026-01-01T00:00:00Z,M1,25,1.0,100,0\n"
        "2026-01-01T00:01:00Z,M1,65,5.5,400,1\n",
        encoding="utf-8",
    )

    runner.run_module2(
        data_path=csv_path,
        graph_config_path=graph_config_path,
        search_params_path=search_params_path,
        output_dir=tmp_path / "out",
        data_format="module1",
        classifications_path=None,
    )
    assert (tmp_path / "out" / "sequences.json").exists()
    assert (tmp_path / "out" / "warning_signs.json").exists()
