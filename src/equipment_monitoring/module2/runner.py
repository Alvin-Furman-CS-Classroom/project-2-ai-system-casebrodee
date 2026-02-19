"""
Main runner for Module 2: End-to-end pipeline execution.

This module provides the run_module2() function that orchestrates:
1. Loading historical data
2. Building the graph
3. Running search algorithms
4. Extracting patterns and ranking warning signs
5. Writing outputs
"""

import json
from pathlib import Path
from typing import List
from .io import load_timestamped_csv, HistoricalRecord
from .config import GraphConfig, SearchParams
from .graph import build_graph, Graph
from .search import discover_failure_sequences, a_star, heuristic_time_to_failure, heuristic_sensor_distance
from .patterns import extract_sequences, rank_warning_signs, FailureSequence, WarningSign


def run_module2(
    data_path: Path,
    graph_config_path: Path,
    search_params_path: Path,
    output_dir: Path
) -> None:
    """
    Run the complete Module 2 pipeline.
    
    Args:
        data_path: Path to historical sensor data CSV
        graph_config_path: Path to graph configuration JSON
        search_params_path: Path to search parameters JSON
        output_dir: Directory to write outputs
    
    Outputs:
        - sequences.json: Discovered failure sequences
        - warning_signs.json: Ranked warning signs
        - Optional: visualization plots (if implemented)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Load configuration
    graph_config = GraphConfig.from_json(graph_config_path)
    search_params = SearchParams.from_json(search_params_path)
    
    # 2. Load historical data
    records = load_timestamped_csv(data_path)
    
    # OPTIMIZATION: For large datasets, sample to improve performance
    # Prioritize records with failures to ensure we find patterns
    max_records = 1000  # Limit to 1000 records for reasonable performance
    if len(records) > max_records:
        import random
        # Separate failure and non-failure records
        failure_records = [r for r in records if r.failure_label]
        normal_records = [r for r in records if not r.failure_label]
        
        # Keep all failures (or up to half of max), fill rest with normal records
        failure_sample_size = min(len(failure_records), max_records // 2)
        normal_sample_size = max_records - failure_sample_size
        
        sampled_failures = random.sample(failure_records, min(failure_sample_size, len(failure_records)))
        sampled_normal = random.sample(normal_records, min(normal_sample_size, len(normal_records)))
        
        records = sampled_failures + sampled_normal
        random.shuffle(records)  # Mix them up
        print(f"Sampled {len(records)} records ({len(sampled_failures)} failures, {len(sampled_normal)} normal) from {len(failure_records) + len(normal_records)} total for performance...")
    
    # 3. Build graph
    graph = build_graph(records, graph_config)
    
    # 4. Discover failure sequences using BFS/DFS
    paths = discover_failure_sequences(graph, search_params)
    
    # 5. Extract and aggregate sequences
    sequences = extract_sequences(paths, search_params.min_pattern_length)
    
    # 6. Rank warning signs
    warning_signs = rank_warning_signs(sequences, graph)
    
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
