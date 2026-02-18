"""
Graph building for Module 2: Construct state graph from historical records.

This module builds a graph structure where:
- Nodes represent discretized equipment states (combinations of sensor bins)
- Edges represent transitions between states over time
- Goal states are marked where failures occur
"""

from typing import Dict, List, Set, Tuple
from .io import HistoricalRecord
from .config import GraphConfig


class State:
    """
    Represents a discretized equipment state.
    
    A state is defined by the combination of bin labels for selected sensors.
    For example, if state_components = ["Temperature", "Vibration_Level"],
    a state might be ("medium", "high") meaning medium temperature and high vibration.
    """
    
    def __init__(self, machine_id: str, sensor_bins: Tuple[str, ...]):
        """
        Initialize a state.
        
        Args:
            machine_id: The machine this state belongs to
            sensor_bins: Tuple of bin labels for each sensor in state_components order
        """
        self.machine_id = machine_id
        self.sensor_bins = sensor_bins
    
    def __hash__(self) -> int:
        return hash((self.machine_id, self.sensor_bins))
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, State):
            return False
        return self.machine_id == other.machine_id and self.sensor_bins == other.sensor_bins
    
    def __repr__(self) -> str:
        return f"State(machine={self.machine_id}, bins={self.sensor_bins})"


class Graph:
    """
    Graph structure representing equipment state transitions.
    
    The graph is built from historical records by:
    1. Discretizing sensor values into bins
    2. Creating states from combinations of bins
    3. Adding edges for time-ordered transitions
    4. Marking failure states
    """
    
    def __init__(self):
        """Initialize an empty graph."""
        self.nodes: Set[State] = set()
        self.edges: Dict[State, List[State]] = {}  # Adjacency list
        self.failure_states: Set[State] = set()  # States where failures occur
        self.state_to_records: Dict[State, List[HistoricalRecord]] = {}  # Records mapping to each state
    
    def add_node(self, state: State) -> None:
        """Add a node to the graph."""
        self.nodes.add(state)
        if state not in self.edges:
            self.edges[state] = []
        if state not in self.state_to_records:
            self.state_to_records[state] = []
    
    def add_edge(self, from_state: State, to_state: State) -> None:
        """
        Add a directed edge from from_state to to_state.
        
        Args:
            from_state: Source state
            to_state: Target state
        """
        self.add_node(from_state)
        self.add_node(to_state)
        if to_state not in self.edges[from_state]:
            self.edges[from_state].append(to_state)
    
    def mark_failure_state(self, state: State) -> None:
        """Mark a state as a failure state."""
        self.add_node(state)
        self.failure_states.add(state)
    
    def get_neighbors(self, state: State) -> List[State]:
        """Get all neighbors (successor states) of a given state."""
        return self.edges.get(state, [])
    
    def is_failure_state(self, state: State) -> bool:
        """Check if a state is marked as a failure state."""
        return state in self.failure_states


def states_differ_by_one(s1: State, s2: State, ignore_machine_id: bool = False) -> bool:
    """
    Check if two states differ by exactly one sensor bin.
    
    This is used to connect similar states in the graph when we don't have
    temporal sequences (e.g., when each machine has only one record).
    
    Args:
        s1: First state
        s2: Second state
        ignore_machine_id: If True, ignore machine_id when comparing (for cross-machine patterns)
    """
    if not ignore_machine_id and s1.machine_id != s2.machine_id:
        return False
    if len(s1.sensor_bins) != len(s2.sensor_bins):
        return False
    
    differences = sum(1 for b1, b2 in zip(s1.sensor_bins, s2.sensor_bins) if b1 != b2)
    return differences == 1


def build_graph(
    records: List[HistoricalRecord],
    graph_config: GraphConfig
) -> Graph:
    """
    Build a graph from historical records.
    
    If records have temporal ordering (multiple records per machine), builds
    edges based on time sequence. Otherwise, builds edges based on state similarity
    (states that differ by one sensor bin).
    
    Args:
        records: List of historical records (should be sorted by machine_id and time_key)
        graph_config: Configuration for discretization and state components
    
    Returns:
        Graph object with nodes, edges, and failure states marked
    """
    graph = Graph()
    
    # Group records by machine_id
    machine_records: Dict[str, List[HistoricalRecord]] = {}
    for record in records:
        if record.machine_id not in machine_records:
            machine_records[record.machine_id] = []
        machine_records[record.machine_id].append(record)
    
    # Check if we have temporal data (multiple records per machine)
    has_temporal_data = any(len(recs) > 1 for recs in machine_records.values())
    
    # Convert all records to states first
    all_states: List[State] = []
    state_to_record: Dict[State, HistoricalRecord] = {}
    
    for machine_id, machine_record_list in machine_records.items():
        # Sort by time_key to ensure correct ordering
        machine_record_list.sort(key=lambda r: r.time_key)
        
        for record in machine_record_list:
            # Discretize sensors
            discretized = graph_config.discretize_sensors(record.sensors)
            
            # Build state from selected components
            sensor_bins = tuple(
                discretized.get(sensor, "unknown")
                for sensor in graph_config.state_components
            )
            state = State(machine_id, sensor_bins)
            
            # Check if this state already exists in the graph (reuse it)
            if state in graph.nodes:
                # Find the existing state object
                existing_state = next(s for s in graph.nodes if s == state)
                state = existing_state
            else:
                # Add new state to graph
                graph.add_node(state)
            
            # Add record to state mapping
            graph.state_to_records[state].append(record)
            state_to_record[state] = record
            
            # Mark failure states
            if record.failure_label:
                graph.mark_failure_state(state)
            
            all_states.append(state)
    
    # Build edges
    if has_temporal_data:
        # Temporal mode: connect consecutive states within each machine
        for machine_id, machine_record_list in machine_records.items():
            machine_record_list.sort(key=lambda r: r.time_key)
            states: List[State] = []
            for record in machine_record_list:
                discretized = graph_config.discretize_sensors(record.sensors)
                sensor_bins = tuple(
                    discretized.get(sensor, "unknown")
                    for sensor in graph_config.state_components
                )
                state = State(machine_id, sensor_bins)
                if state in graph.nodes:
                    state = next(s for s in graph.nodes if s == state)
                states.append(state)
            
            # Add edges between consecutive states
            for i in range(len(states) - 1):
                graph.add_edge(states[i], states[i + 1])
    else:
        # Similarity mode: connect states that differ by one sensor bin
        # OPTIMIZATION: Limit connections to prevent graph explosion
        # Only connect each state to a limited number of similar states
        states_list = list(graph.nodes)
        max_neighbors_per_state = 20  # Limit connections per state
        
        # Build edges more efficiently: for each state, find its nearest neighbors
        for state1 in states_list:
            neighbors_found = 0
            for state2 in states_list:
                if state1 == state2:
                    continue
                if neighbors_found >= max_neighbors_per_state:
                    break
                if states_differ_by_one(state1, state2, ignore_machine_id=True):
                    graph.add_edge(state1, state2)
                    neighbors_found += 1
    
    return graph
