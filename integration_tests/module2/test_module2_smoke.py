"""Integration test for Module 2: End-to-end smoke test.

This test runs the full Module 2 pipeline on a small slice of the timestamped dataset
and asserts that outputs are generated correctly.
"""

import pytest
from pathlib import Path

from equipment_monitoring.module2 import runner


def test_module2_smoke(tmp_path: Path) -> None:
    """Run Module 2 pipeline on a small dataset and verify outputs."""
    # Use the actual timestamped dataset
    data_path = Path(__file__).parent.parent.parent / "src" / "data" / "machine_failure_data_timestamp.csv"
    
    if not data_path.exists():
        pytest.skip(f"Dataset not found at {data_path}")
    
    graph_config_path = Path(__file__).parent.parent.parent / "src" / "data" / "module2" / "graph_config.json"
    search_params_path = Path(__file__).parent.parent.parent / "src" / "data" / "module2" / "search_params.json"
    output_dir = tmp_path / "module2_outputs"
    
    # Run Module 2
    runner.run_module2(
        data_path=data_path,
        graph_config_path=graph_config_path,
        search_params_path=search_params_path,
        output_dir=output_dir
    )
    
    # Verify outputs exist
    sequences_file = output_dir / "sequences.json"
    warning_signs_file = output_dir / "warning_signs.json"
    
    assert sequences_file.exists(), "sequences.json should be created"
    assert warning_signs_file.exists(), "warning_signs.json should be created"
    
    # Verify outputs are valid JSON
    import json
    with open(sequences_file) as f:
        sequences_data = json.load(f)
        assert "sequences" in sequences_data
    
    with open(warning_signs_file) as f:
        warning_signs_data = json.load(f)
        assert "warning_signs" in warning_signs_data
