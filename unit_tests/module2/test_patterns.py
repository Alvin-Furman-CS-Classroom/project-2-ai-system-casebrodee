"""Unit tests for Module 2 pattern extraction (`patterns` module).

These tests exercise:
- Extracting sequences from search paths
- Aggregating sequences by frequency
- Ranking warning signs by predictive score
"""

import pytest

from equipment_monitoring.module2 import graph, patterns, config


def test_extract_sequences_aggregates_by_frequency() -> None:
    """Test that extract_sequences aggregates duplicate sequences."""
    # Create paths with some duplicates
    state_a = graph.State("MACHINE_001", ("low", "low"))
    state_b = graph.State("MACHINE_001", ("medium", "low"))
    state_c = graph.State("MACHINE_001", ("high", "high"))
    
    paths = [
        [state_a, state_b, state_c],  # Sequence 1
        [state_a, state_b, state_c],  # Duplicate
        [state_a, state_b, state_c],  # Duplicate
        [state_a, state_c],  # Different sequence
    ]
    
    sequences = patterns.extract_sequences(paths, min_pattern_length=2)
    
    # Should aggregate duplicates
    assert len(sequences) == 2
    
    # First sequence should have frequency 3
    seq_with_freq_3 = [s for s in sequences if s.frequency == 3]
    assert len(seq_with_freq_3) == 1


def test_extract_sequences_filters_by_min_length() -> None:
    """Test that extract_sequences filters out sequences below min_pattern_length."""
    state_a = graph.State("MACHINE_001", ("low", "low"))
    state_b = graph.State("MACHINE_001", ("medium", "low"))
    state_c = graph.State("MACHINE_001", ("high", "high"))
    
    paths = [
        [state_a, state_c],  # Length 2 (after removing failure)
        [state_a, state_b, state_c],  # Length 3
    ]
    
    sequences = patterns.extract_sequences(paths, min_pattern_length=3)
    
    # Should only include the longer sequence
    assert len(sequences) == 1
    assert len(sequences[0].sequence) == 2  # state_a, state_b (state_c is failure, excluded)


def test_rank_warning_signs_sorts_by_score() -> None:
    """Test that rank_warning_signs sorts by predictive_score."""
    state_a = graph.State("MACHINE_001", ("low", "low"))
    state_b = graph.State("MACHINE_001", ("medium", "low"))
    state_c = graph.State("MACHINE_001", ("high", "high"))
    
    sequences = [
        patterns.FailureSequence(
            sequence=[state_a, state_b],
            frequency=5,
            machines={"MACHINE_001"}
        ),
        patterns.FailureSequence(
            sequence=[state_a, state_c],
            frequency=15,  # Higher frequency
            machines={"MACHINE_001"}
        ),
    ]
    
    # Create a minimal graph
    g = graph.Graph()
    g.add_node(state_a)
    g.add_node(state_b)
    g.add_node(state_c)
    
    warning_signs = patterns.rank_warning_signs(sequences, g)
    
    assert len(warning_signs) == 2
    # Should be sorted by predictive_score (highest first)
    assert warning_signs[0].predictive_score >= warning_signs[1].predictive_score
