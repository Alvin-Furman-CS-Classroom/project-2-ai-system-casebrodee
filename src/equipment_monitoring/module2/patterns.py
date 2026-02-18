"""
Pattern extraction and ranking for Module 2: Convert search results into sequences and warning signs.

This module processes paths discovered by search algorithms and:
- Aggregates them into failure sequences with frequency statistics
- Ranks warning signs by predictive power
- Calculates timing statistics
"""

from typing import List, Dict, Set
from collections import Counter, defaultdict
from .graph import Graph
from .graph import State
from .config import SearchParams


class FailureSequence:
    """
    Represents a discovered sequence that precedes failures.
    
    Attributes:
        sequence: List of states in the sequence
        frequency: Number of times this sequence was observed
        machines: Set of machine IDs where this sequence occurred
        avg_time_to_failure: Average time steps from sequence end to failure
    """
    
    def __init__(
        self,
        sequence: List[State],
        frequency: int = 1,
        machines: Set[str] = None,
        avg_time_to_failure: float = 0.0
    ):
        self.sequence = sequence
        self.frequency = frequency
        self.machines = machines or set()
        self.avg_time_to_failure = avg_time_to_failure
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sequence": [str(state) for state in self.sequence],
            "frequency": self.frequency,
            "avg_time_to_failure": self.avg_time_to_failure,
            "machines": list(self.machines)
        }


class WarningSign:
    """
    Represents a ranked warning sign with predictive metrics.
    
    Attributes:
        pattern: Human-readable description of the pattern
        predictive_score: Score indicating how predictive this pattern is (0-1)
        frequency: Number of times this pattern preceded a failure
        false_positive_rate: Rate of false positives (pattern occurred without failure)
    """
    
    def __init__(
        self,
        pattern: str,
        predictive_score: float,
        frequency: int,
        false_positive_rate: float = 0.0
    ):
        self.pattern = pattern
        self.predictive_score = predictive_score
        self.frequency = frequency
        self.false_positive_rate = false_positive_rate
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "pattern": self.pattern,
            "predictive_score": self.predictive_score,
            "frequency": self.frequency,
            "false_positive_rate": self.false_positive_rate
        }


def extract_sequences(
    paths: List[List[State]],
    min_pattern_length: int = 3
) -> List[FailureSequence]:
    """
    Extract and aggregate failure sequences from search paths.
    
    Args:
        paths: List of paths (each path is a list of states ending in failure)
        min_pattern_length: Minimum length for a sequence to be considered
    
    Returns:
        List of FailureSequence objects with frequency statistics
    """
    # Count occurrences of each sequence
    sequence_counter: Counter = Counter()
    sequence_to_machines: Dict[tuple, Set[str]] = defaultdict(set)
    
    for path in paths:
        if len(path) < min_pattern_length:
            continue
        
        # Extract sequence (all states except the failure state itself)
        sequence = tuple(path[:-1])  # Exclude final failure state
        sequence_counter[sequence] += 1
        
        # Track which machines this sequence occurred in
        if path:
            machine_id = path[0].machine_id
            sequence_to_machines[sequence].add(machine_id)
    
    # Build FailureSequence objects
    sequences = []
    for sequence_tuple, frequency in sequence_counter.items():
        sequence_list = list(sequence_tuple)
        machines = sequence_to_machines[sequence_tuple]
        
        sequences.append(FailureSequence(
            sequence=sequence_list,
            frequency=frequency,
            machines=machines,
            avg_time_to_failure=0.0  # TODO: Calculate from actual time differences
        ))
    
    # Sort by frequency (most common first)
    sequences.sort(key=lambda s: s.frequency, reverse=True)
    
    return sequences


def rank_warning_signs(
    sequences: List[FailureSequence],
    graph
) -> List[WarningSign]:
    """
    Rank warning signs by predictive power.
    
    Args:
        sequences: List of failure sequences
        graph: The state graph (for calculating false positive rates)
    
    Returns:
        List of WarningSign objects ranked by predictive_score
    """
    warning_signs = []
    
    for seq in sequences:
        # Create human-readable pattern description
        if len(seq.sequence) > 0:
            first_state = seq.sequence[0]
            last_state = seq.sequence[-1]
            pattern = f"State transition: {first_state.sensor_bins} -> {last_state.sensor_bins} ({len(seq.sequence)} steps)"
        else:
            pattern = "Empty sequence"
        
        # Calculate predictive score (simple: based on frequency)
        # More sophisticated: could use actual failure prediction accuracy
        predictive_score = min(seq.frequency / 10.0, 1.0)  # Normalize to 0-1
        
        # TODO: Calculate false positive rate by checking how often this sequence
        # occurred without leading to failure
        false_positive_rate = 0.0
        
        warning_signs.append(WarningSign(
            pattern=pattern,
            predictive_score=predictive_score,
            frequency=seq.frequency,
            false_positive_rate=false_positive_rate
        ))
    
    # Sort by predictive score (highest first)
    warning_signs.sort(key=lambda w: w.predictive_score, reverse=True)
    
    return warning_signs
