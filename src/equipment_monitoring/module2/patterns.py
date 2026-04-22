"""
Pattern extraction and ranking for Module 2: Convert search results into sequences and warning signs.

This module processes paths discovered by search algorithms and:
- Aggregates them into failure sequences with frequency statistics
- Ranks warning signs by predictive power
- Calculates timing statistics
"""

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Mapping, Optional, Set, Union
from .graph import Graph
from .graph import State


@dataclass
class FailureSequence:
    """
    Represents a discovered sequence that precedes failures.
    
    Attributes:
        sequence: List of states in the sequence
        frequency: Number of times this sequence was observed
        machines: Set of machine IDs where this sequence occurred
        avg_time_to_failure: Average time steps from sequence end to failure
    """
    
    sequence: List[State]
    frequency: int = 1
    machines: Optional[Set[str]] = None
    avg_time_to_failure: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sequence": [str(state) for state in self.sequence],
            "frequency": self.frequency,
            "avg_time_to_failure": self.avg_time_to_failure,
            "machines": list(self.machines or set())
        }


@dataclass
class WarningSign:
    """
    Represents a ranked warning sign with predictive metrics.
    
    Attributes:
        pattern: Human-readable description of the pattern
        predictive_score: Score indicating how predictive this pattern is (0-1)
        frequency: Number of times this pattern preceded a failure
        false_positive_rate: Rate of false positives (pattern occurred without failure)
    """
    
    pattern: str
    predictive_score: float
    frequency: int
    false_positive_rate: float = 0.0
    module1_anomaly_rate: float | None = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        data = {
            "pattern": self.pattern,
            "predictive_score": self.predictive_score,
            "frequency": self.frequency,
            "false_positive_rate": self.false_positive_rate,
        }
        if self.module1_anomaly_rate is not None:
            data["module1_anomaly_rate"] = self.module1_anomaly_rate
        return data


def _get_time_difference(
    time1: Union[datetime, int, float],
    time2: Union[datetime, int, float],
) -> float:
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


def _find_matching_neighbor(current_state: State, target_state: State, graph: Graph) -> State | None:
    for neighbor in graph.get_neighbors(current_state):
        if neighbor == target_state:
            return neighbor
    return None


def _follow_sequence(graph: Graph, sequence: List[State], start_state: State) -> State | None:
    current_state = start_state
    for next_state in sequence[1:]:
        matched_neighbor = _find_matching_neighbor(current_state, next_state, graph)
        if matched_neighbor is None:
            return None
        current_state = matched_neighbor
    return current_state


def _path_leads_to_failure(graph: Graph, start_state: State, max_search_depth: int) -> bool:
    visited = {start_state}
    queue = deque([(start_state, 0)])
    while queue:
        current, depth = queue.popleft()
        if graph.is_failure_state(current):
            return True
        if depth >= max_search_depth:
            continue
        for neighbor in graph.get_neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))
    return False


def _count_non_failure_continuations(graph: Graph, end_state: State, max_search_depth: int) -> int:
    neighbors = graph.get_neighbors(end_state)
    if not neighbors:
        return 1 if not graph.is_failure_state(end_state) else 0

    false_positives = 0
    for neighbor in neighbors:
        if graph.is_failure_state(neighbor):
            continue
        if not _path_leads_to_failure(graph, neighbor, max_search_depth):
            false_positives += 1
    return false_positives


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
    matching_start_states = [state for state in graph.nodes if state == sequence[0]]

    for start_state in matching_start_states:
        end_state = _follow_sequence(graph, sequence, start_state)
        if end_state is None or graph.is_failure_state(end_state):
            continue
        false_positives += _count_non_failure_continuations(graph, end_state, max_search_depth)

    return false_positives


def _build_pattern_label(sequence: List[State]) -> str:
    if sequence:
        first_state = sequence[0]
        last_state = sequence[-1]
        return (
            f"State transition: {first_state.sensor_bins} -> "
            f"{last_state.sensor_bins} ({len(sequence)} steps)"
        )
    return "Empty sequence"


def _predictive_metrics(true_positives: int, false_positives: int) -> tuple[float, float]:
    total_occurrences = true_positives + false_positives
    false_positive_rate = false_positives / total_occurrences if total_occurrences > 0 else 0.0
    if total_occurrences == 0:
        return min(true_positives / 10.0, 1.0), false_positive_rate
    precision = true_positives / total_occurrences
    frequency_weight = min(true_positives / 10.0, 1.0)
    predictive_score = precision * 0.7 + frequency_weight * 0.3
    return predictive_score, false_positive_rate


def _sequence_module1_anomaly_rate(
    machines: Set[str] | None,
    module1_anomaly_rates: Mapping[str, float] | None,
) -> float | None:
    if not machines or not module1_anomaly_rates:
        return None
    matched_rates = [module1_anomaly_rates[machine] for machine in sorted(machines) if machine in module1_anomaly_rates]
    if not matched_rates:
        return None
    return sum(matched_rates) / len(matched_rates)


def rank_warning_signs(
    sequences: List[FailureSequence],
    graph: Graph,
    module1_anomaly_rates: Mapping[str, float] | None = None,
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
        pattern = _build_pattern_label(seq.sequence)
        false_positives = _count_false_positives(graph, seq.sequence)
        predictive_score, false_positive_rate = _predictive_metrics(seq.frequency, false_positives)
        warning_signs.append(WarningSign(
            pattern=pattern,
            predictive_score=predictive_score,
            frequency=seq.frequency,
            false_positive_rate=false_positive_rate,
            module1_anomaly_rate=_sequence_module1_anomaly_rate(seq.machines, module1_anomaly_rates),
        ))
    
    # Sort by predictive score (highest first)
    warning_signs.sort(key=lambda w: w.predictive_score, reverse=True)
    
    return warning_signs
