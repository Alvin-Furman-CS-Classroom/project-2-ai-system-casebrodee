"""
Pattern extraction and ranking for Module 2: Convert search results into sequences and warning signs.

This module processes paths discovered by search algorithms and:
- Aggregates them into failure sequences with frequency statistics
- Ranks warning signs by predictive power
- Calculates timing statistics
"""

from typing import List, Dict, Set
from collections import Counter, defaultdict
from datetime import datetime
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


def _get_time_difference(time1, time2) -> float:
    """
    Calculate time difference between two time keys.
    
    Returns difference in seconds (for datetime) or as-is (for numeric).
    """
    if isinstance(time1, datetime) and isinstance(time2, datetime):
        delta = time2 - time1
        return delta.total_seconds()
    elif isinstance(time1, (int, float)) and isinstance(time2, (int, float)):
        return abs(time2 - time1)
    else:
        # Mixed types: convert datetime to timestamp
        t1 = time1.timestamp() if isinstance(time1, datetime) else time1
        t2 = time2.timestamp() if isinstance(time2, datetime) else time2
        return abs(t2 - t1)


def extract_sequences(
    paths: List[List[State]],
    graph: Graph,
    min_pattern_length: int = 3
) -> List[FailureSequence]:
    """
    Extract and aggregate failure sequences from search paths.
    
    Args:
        paths: List of paths (each path is a list of states ending in failure)
        graph: The state graph (for accessing records and timestamps)
        min_pattern_length: Minimum length for a sequence to be considered
    
    Returns:
        List of FailureSequence objects with frequency statistics and timing
    """
    # Count occurrences of each sequence and collect time differences
    sequence_counter: Counter = Counter()
    sequence_to_machines: Dict[tuple, Set[str]] = defaultdict(set)
    sequence_to_times: Dict[tuple, List[float]] = defaultdict(list)
    
    for path in paths:
        if len(path) < min_pattern_length:
            continue
        
        # Extract sequence (all states except the failure state itself)
        sequence = tuple(path[:-1])  # Exclude final failure state
        failure_state = path[-1]  # The failure state
        
        sequence_counter[sequence] += 1
        
        # Track which machines this sequence occurred in
        if path:
            machine_id = path[0].machine_id
            sequence_to_machines[sequence].add(machine_id)
        
        # Calculate time to failure: time difference between last sequence state and failure state
        if sequence and failure_state:
            last_sequence_state = path[-2]  # Last state before failure
            
            # Get records for both states
            last_state_records = graph.state_to_records.get(last_sequence_state, [])
            failure_state_records = graph.state_to_records.get(failure_state, [])
            
            if last_state_records and failure_state_records:
                # Use the earliest record from each state (or average if multiple)
                last_time = last_state_records[0].time_key
                failure_time = failure_state_records[0].time_key
                
                time_diff = _get_time_difference(last_time, failure_time)
                sequence_to_times[sequence].append(time_diff)
    
    # Build FailureSequence objects
    sequences = []
    for sequence_tuple, frequency in sequence_counter.items():
        sequence_list = list(sequence_tuple)
        machines = sequence_to_machines[sequence_tuple]
        
        # Calculate average time to failure
        time_diffs = sequence_to_times.get(sequence_tuple, [])
        avg_time = sum(time_diffs) / len(time_diffs) if time_diffs else 0.0
        
        sequences.append(FailureSequence(
            sequence=sequence_list,
            frequency=frequency,
            machines=machines,
            avg_time_to_failure=avg_time
        ))
    
    # Sort by frequency (most common first)
    sequences.sort(key=lambda s: s.frequency, reverse=True)
    
    return sequences


def _count_false_positives(
    graph: Graph,
    sequence: List[State],
    max_search_depth: int = 20
) -> int:
    """
    Count how many times a sequence occurs without leading to failure.
    
    Args:
        graph: The state graph
        sequence: The sequence to search for
        max_search_depth: Maximum depth to search from sequence end
    
    Returns:
        Number of false positives (sequence occurred but didn't lead to failure)
    """
    if not sequence:
        return 0
    
    false_positives = 0
    
    # Find all states that match the first state in the sequence
    matching_start_states = [
        state for state in graph.nodes
        if state == sequence[0]
    ]
    
    for start_state in matching_start_states:
        # Try to follow the sequence path
        current_state = start_state
        sequence_matched = True
        
        for next_state_in_sequence in sequence[1:]:
            neighbors = graph.get_neighbors(current_state)
            # Check if any neighbor matches the next state in sequence
            matching_neighbor = None
            for neighbor in neighbors:
                if neighbor == next_state_in_sequence:
                    matching_neighbor = neighbor
                    break
            
            if matching_neighbor is None:
                sequence_matched = False
                break
            
            current_state = matching_neighbor
        
        if sequence_matched:
            # Sequence matched! Check each continuation path separately
            end_state = current_state
            
            # If end state itself is a failure, skip (this is a true positive, already counted)
            if graph.is_failure_state(end_state):
                continue
            
            neighbors = graph.get_neighbors(end_state)
            
            # Check each neighbor path separately
            # If a neighbor is a failure state, that's a true positive (already in frequency)
            # If a neighbor is not a failure and doesn't lead to failure, that's a false positive
            for neighbor in neighbors:
                if graph.is_failure_state(neighbor):
                    # This path leads to failure - true positive, skip
                    continue
                
                # Check if this neighbor path leads to failure within search depth
                visited = {end_state, neighbor}
                queue = [neighbor]
                found_failure = False
                
                for _ in range(max_search_depth):
                    if not queue:
                        break
                    current = queue.pop(0)
                    if graph.is_failure_state(current):
                        found_failure = True
                        break
                    for next_neighbor in graph.get_neighbors(current):
                        if next_neighbor not in visited:
                            visited.add(next_neighbor)
                            queue.append(next_neighbor)
                
                if not found_failure:
                    # This path doesn't lead to failure - false positive
                    false_positives += 1
            
            # If end state has no neighbors and isn't a failure, that's also a false positive
            if not neighbors and not graph.is_failure_state(end_state):
                false_positives += 1
    
    return false_positives


def rank_warning_signs(
    sequences: List[FailureSequence],
    graph: Graph
) -> List[WarningSign]:
    """
    Rank warning signs by predictive power.
    
    Args:
        sequences: List of failure sequences (frequency already represents true positives)
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
        
        # Calculate false positive rate
        # seq.frequency is the number of true positives (sequences that led to failure)
        # Search graph for sequences that match but don't lead to failure
        false_positives = _count_false_positives(graph, seq.sequence)
        true_positives = seq.frequency  # Use frequency as true positives
        total_occurrences = true_positives + false_positives
        false_positive_rate = false_positives / total_occurrences if total_occurrences > 0 else 0.0
        
        # Calculate predictive score based on precision (true_positives / total_occurrences)
        # This is more meaningful than just frequency
        if total_occurrences > 0:
            precision = true_positives / total_occurrences
            # Combine precision with frequency (normalized) for final score
            frequency_weight = min(seq.frequency / 10.0, 1.0)
            predictive_score = (precision * 0.7 + frequency_weight * 0.3)
        else:
            # If no occurrences found in graph search, use frequency-based score
            predictive_score = min(seq.frequency / 10.0, 1.0)
        
        warning_signs.append(WarningSign(
            pattern=pattern,
            predictive_score=predictive_score,
            frequency=seq.frequency,
            false_positive_rate=false_positive_rate
        ))
    
    # Sort by predictive score (highest first)
    warning_signs.sort(key=lambda w: w.predictive_score, reverse=True)
    
    return warning_signs
