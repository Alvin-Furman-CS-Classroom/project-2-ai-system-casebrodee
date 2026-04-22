"""
Main runner for Module 2: End-to-end pipeline execution.

This module provides the run_module2() function that orchestrates:
1. Loading historical data (timestamped CSV or Module 1–schema CSV)
2. Building the graph
3. Running search algorithms
4. Extracting patterns and ranking warning signs
5. Writing outputs
"""

import json
from pathlib import Path
from typing import Optional
from .io import (
    load_classification_anomaly_rates,
    load_module1_schema_csv,
    load_timestamped_csv,
)
from .config import GraphConfig, SearchParams
from .graph import build_graph
from .search import discover_failure_sequences
from .patterns import extract_sequences, rank_warning_signs


def run_module2(
    data_path: Path,
    graph_config_path: Path,
    search_params_path: Path,
    output_dir: Path,
    *,
    data_format: str = "timestamped",
    classifications_path: Optional[Path] = None,
) -> None:
    """
    Run the complete Module 2 pipeline.

    Args:
        data_path: Path to historical sensor data CSV
        graph_config_path: Path to graph configuration JSON
        search_params_path: Path to search parameters JSON
        output_dir: Directory to write outputs
        data_format: "timestamped" (default) for Machine_ID/Timestamp/Failure_Status CSV,
            or "module1" for timestamp/equipment_id/temperature/vibration/pressure/failure_status CSV
            (same schema Module 1 uses; allows one dataset to feed both modules).
        classifications_path: Optional Module 1 ``classifications.jsonl`` used to enrich
            warning signs with per-equipment anomaly-rate context.

    Outputs:
        - sequences.json: Discovered failure sequences
        - warning_signs.json: Ranked warning signs
        - Optional: visualization plots (if implemented)

    Note:
        The graph uses all loaded records (no sampling) and full similarity edges when
        data is not time-series per machine. Path enumeration is bounded by optional
        ``max_total_paths`` and ``max_paths_per_start`` in search params JSON; set them
        to null for no cap (can be very slow on large, dense graphs).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load configuration
    graph_config = GraphConfig.from_json(graph_config_path)
    search_params = SearchParams.from_json(search_params_path)

    # 2. Load historical data
    if data_format == "module1":
        records = load_module1_schema_csv(data_path)
    else:
        records = load_timestamped_csv(data_path)

    # 3. Build graph
    graph = build_graph(records, graph_config)
    
    # 4. Discover failure sequences using BFS/DFS
    paths = discover_failure_sequences(graph, search_params)
    
    # 5. Extract and aggregate sequences
    sequences = extract_sequences(paths, graph, search_params.min_pattern_length)

    # 6. Rank warning signs and optionally enrich with Module 1 anomaly rates.
    module1_anomaly_rates = (
        load_classification_anomaly_rates(classifications_path)
        if classifications_path is not None
        else None
    )
    warning_signs = rank_warning_signs(
        sequences,
        graph,
        module1_anomaly_rates=module1_anomaly_rates,
    )
    
    # 7. Write outputs
    sequences_output = {
        "sequences": [seq.to_dict() for seq in sequences]
    }
    with open(output_dir / "sequences.json", 'w') as f:
        json.dump(sequences_output, f, indent=2)
    
    warning_signs_output = {
        "warning_signs": [ws.to_dict() for ws in warning_signs]
    }
    with open(output_dir / "warning_signs.json", 'w') as f:
        json.dump(warning_signs_output, f, indent=2)
    
    print(f"Module 2 complete. Outputs written to {output_dir}")
    print(f"  - Found {len(sequences)} failure sequences")
    print(f"  - Ranked {len(warning_signs)} warning signs")
