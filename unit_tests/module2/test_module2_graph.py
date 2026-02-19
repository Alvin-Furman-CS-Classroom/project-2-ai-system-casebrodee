"""Unit tests for Module 2 graph building (`graph` module).

These tests exercise:
- Building graphs from historical records
- State discretization
- Edge creation between consecutive states
- Failure state marking
"""

import pytest
from datetime import datetime
from pathlib import Path

from equipment_monitoring.module2 import io, graph, config


def test_build_graph_simple_sequence(tmp_path: Path) -> None:
    """Test building a graph from a simple sequence of states."""
    # Create synthetic records with values that discretize to three distinct states
    # (bins: temp [0,30,50,70,100], vib [0,3,6,10], pressure [0,200,350,500])
    records = [
        io.HistoricalRecord(
            machine_id="MACHINE_001",
            time_key=datetime(2025, 1, 1, 0, 0, 0),
            sensors={"Temperature": 25.0, "Vibration_Level": 1.0, "Pressure": 100.0},
            failure_label=False
        ),
        io.HistoricalRecord(
            machine_id="MACHINE_001",
            time_key=datetime(2025, 1, 1, 0, 10, 0),
            sensors={"Temperature": 45.0, "Vibration_Level": 4.0, "Pressure": 250.0},
            failure_label=False
        ),
        io.HistoricalRecord(
            machine_id="MACHINE_001",
            time_key=datetime(2025, 1, 1, 0, 20, 0),
            sensors={"Temperature": 65.0, "Vibration_Level": 7.0, "Pressure": 400.0},
            failure_label=True
        ),
    ]
    
    # Create a simple graph config
    graph_config = config.GraphConfig(
        discretization={
            "Temperature": config.DiscretizationConfig(
                bins=[0, 30, 50, 70, 100],
                labels=["low", "medium", "high", "very_high"]
            ),
            "Vibration_Level": config.DiscretizationConfig(
                bins=[0, 3.0, 6.0, 10.0],
                labels=["low", "medium", "high"]
            ),
            "Pressure": config.DiscretizationConfig(
                bins=[0, 200, 350, 500],
                labels=["low", "medium", "high"]
            ),
        },
        state_components=["Temperature", "Vibration_Level", "Pressure"]
    )
    
    # Build graph
    g = graph.build_graph(records, graph_config)
    
    # Should have 3 states (one per record)
    assert len(g.nodes) == 3
    
    # Should have 2 edges (A->B, B->C)
    total_edges = sum(len(neighbors) for neighbors in g.edges.values())
    assert total_edges == 2
    
    # Last state should be marked as failure
    failure_states = [s for s in g.nodes if g.is_failure_state(s)]
    assert len(failure_states) == 1


def test_state_equality() -> None:
    """Test State equality and hashing."""
    state1 = graph.State("MACHINE_001", ("medium", "low", "medium"))
    state2 = graph.State("MACHINE_001", ("medium", "low", "medium"))
    state3 = graph.State("MACHINE_001", ("high", "low", "medium"))
    
    assert state1 == state2
    assert state1 != state3
    assert hash(state1) == hash(state2)
    
    # Can be used in sets
    state_set = {state1, state2, state3}
    assert len(state_set) == 2  # state1 and state2 are duplicates


def test_graph_add_node_and_edge() -> None:
    """Test basic graph operations."""
    g = graph.Graph()
    state1 = graph.State("MACHINE_001", ("low", "low"))
    state2 = graph.State("MACHINE_001", ("medium", "low"))
    
    g.add_node(state1)
    assert state1 in g.nodes
    
    g.add_edge(state1, state2)
    assert state2 in g.nodes
    assert state2 in g.get_neighbors(state1)


def test_graph_mark_failure_state() -> None:
    """Test marking failure states."""
    g = graph.Graph()
    state = graph.State("MACHINE_001", ("high", "high"))
    
    g.mark_failure_state(state)
    assert g.is_failure_state(state)
    assert state in g.failure_states
