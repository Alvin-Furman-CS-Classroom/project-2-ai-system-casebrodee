"""End-to-end: Module 1 -> Module 2 -> Module 3 on shared CSV."""

import json
from pathlib import Path

import pytest

from equipment_monitoring.module1 import classifier
from equipment_monitoring.module2 import runner as module2_runner
from equipment_monitoring.module3 import runner as module3_runner


def test_module1_module2_module3_pipeline(tmp_path: Path) -> None:
    repo_root = Path(__file__).parent.parent.parent
    kb_path = repo_root / "src" / "data" / "module3" / "kb.json"
    graph_config_path = repo_root / "src" / "data" / "module2" / "graph_config.json"
    search_params_path = repo_root / "src" / "data" / "module2" / "search_params.json"

    if not kb_path.exists() or not graph_config_path.exists():
        pytest.skip("Module 2/3 data files not found")

    cfg_path = tmp_path / "config.json"
    specs_path = tmp_path / "specs.json"
    csv_path = tmp_path / "readings_with_failures.csv"
    module1_output = tmp_path / "module1_out"
    module2_output = tmp_path / "module2_out"
    module3_output = tmp_path / "module3_out"

    cfg_path.write_text(
        json.dumps(
            {
                "temperature": {"min": 20.0, "max": 80.0},
                "vibration": {"max": 5.0},
                "pressure": {"min": 10.0, "max": 50.0},
            }
        ),
        encoding="utf-8",
    )
    specs_path.write_text("{}", encoding="utf-8")

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

    classifier.run_module1(
        config_path=cfg_path,
        specs_path=specs_path,
        csv_path=csv_path,
        output_dir=module1_output,
    )

    module2_runner.run_module2(
        data_path=csv_path,
        graph_config_path=graph_config_path,
        search_params_path=search_params_path,
        output_dir=module2_output,
        data_format="module1",
        classifications_path=module1_output / "classifications.jsonl",
    )

    module3_runner.run_module3(
        kb_path=kb_path,
        classifications_path=module1_output / "classifications.jsonl",
        sequences_path=module2_output / "sequences.json",
        warning_signs_path=module2_output / "warning_signs.json",
        output_dir=module3_output,
    )

    diag_path = module3_output / "diagnosis.json"
    assert diag_path.exists()
    with open(diag_path, encoding="utf-8") as f:
        out = json.load(f)
    assert "equipment" in out
    assert len(out["equipment"]) == 2
    for block in out["equipment"]:
        assert "equipment_id" in block
        assert "diagnoses" in block
        assert "primitive_facts" in block
        assert "meta" in block
    # At least one equipment should get a non-empty diagnosis from KB + synthetic data
    assert any(len(b["diagnoses"]) > 0 for b in out["equipment"])
