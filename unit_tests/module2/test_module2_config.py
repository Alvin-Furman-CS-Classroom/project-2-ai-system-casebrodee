"""Unit tests for Module 2 configuration (`config` module).

These tests exercise:
- GraphConfig and SearchParams loading from JSON
- Error handling for invalid or missing config keys
"""

import pytest
from pathlib import Path

from equipment_monitoring.module2 import config


def test_graph_config_from_json_missing_state_components_raises(tmp_path: Path) -> None:
    """Test that loading graph config without state_components raises."""
    json_path = tmp_path / "graph_config.json"
    json_path.write_text(
        '{"discretization": {"Temperature": {"bins": [0, 50, 100], "labels": ["low", "high"]}}}',
        encoding="utf-8",
    )
    with pytest.raises(KeyError):
        config.GraphConfig.from_json(json_path)


def test_search_params_from_json_valid(tmp_path: Path) -> None:
    """Test loading valid search params from JSON."""
    json_path = tmp_path / "search_params.json"
    json_path.write_text(
        '{"max_depth": 20, "min_pattern_length": 2, "heuristic": "time_to_failure"}',
        encoding="utf-8",
    )
    params = config.SearchParams.from_json(json_path)
    assert params.max_depth == 20
    assert params.min_pattern_length == 2
    assert params.heuristic == "time_to_failure"
