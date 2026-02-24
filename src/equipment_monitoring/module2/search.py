"""
Search algorithms for Module 2: BFS, DFS, and A* to discover failure sequences.

This module implements:
- BFS (Breadth-First Search) for exhaustive path enumeration
- DFS (Depth-First Search) for deep exploration
- A* (A-star) with configurable heuristics for optimal path finding
"""

from typing import List, Callable, Optional, Tuple, Dict, Set
from collections import deque
import heapq
from .graph import Graph, State
from .config import SearchParams

# Limits for discover_failure_sequences to keep runtime reasonable
DEFAULT_MAX_PATHS_PER_START = 5
DEFAULT_MAX_TOTAL_PATHS = 100


class SearchNode:
    """
    Node in the search tree for tracking paths.
    
    Attributes:
        state: The current state
        path: List of states from start to current state
        cost: Accumulated cost to reach this node
        heuristic_cost: Estimated cost from this node to goal
    """
    
    def __init__(
        self,
        state: State,
        path: List[State],
        cost: float = 0.0,
        heuristic_cost: float = 0.0
    ):
        self.state = state
        self.path = path
        self.cost = cost
        self.heuristic_cost = heuristic_cost
    
    @property
    def total_cost(self) -> float:
        """Total cost for A* (cost + heuristic)."""
        return self.cost + self.heuristic_cost
    
    def __lt__(self, other: 'SearchNode') -> bool:
        """For heapq comparison (A* priority queue)."""
        return self.total_cost < other.total_cost


def bfs(
    graph: Graph,
    start_state: State,
    goal_test: Callable[[State], bool],
    max_depth: int = 50,
    max_paths: int = 10
) -> List[List[State]]:
    """
    Breadth-First Search to find all paths from start to goal states.
    
    Args:
        graph: The state graph to search
        start_state: Starting state
        goal_test: Function that returns True for goal states
        max_depth: Maximum depth to search
        max_paths: Maximum number of paths to find (early termination)
    
    Returns:
        List of paths (each path is a list of states) from start to goal
    """
    paths: List[List[State]] = []
    queue = deque([SearchNode(start_state, [start_state])])
    visited_at_depth: Dict[Tuple[State, int], bool] = {}  # (state, depth) -> visited
    
    while queue and len(paths) < max_paths:
        node = queue.popleft()
        current_state = node.state
        depth = len(node.path) - 1
        
        # Check depth limit
        if depth >= max_depth:
            continue
        
        # Check if we've visited this state at this depth before
        key = (current_state, depth)
        if key in visited_at_depth:
            continue
        visited_at_depth[key] = True
        
        # Check if we reached a goal
        if goal_test(current_state):
            paths.append(node.path)
            if len(paths) >= max_paths:
                break
            continue
        
        # Explore neighbors
        for neighbor in graph.get_neighbors(current_state):
            new_path = node.path + [neighbor]
            queue.append(SearchNode(neighbor, new_path))
    
    return paths


def dfs(
    graph: Graph,
    start_state: State,
    goal_test: Callable[[State], bool],
    max_depth: int = 50,
    max_paths: Optional[int] = None
) -> List[List[State]]:
    """
    Depth-First Search to find paths from start to goal states.

    Args:
        graph: The state graph to search
        start_state: Starting state
        goal_test: Function that returns True for goal states
        max_depth: Maximum depth to search
        max_paths: If set, stop after finding this many paths (None = no limit)

    Returns:
        List of paths (each path is a list of states) from start to goal
    """
    paths: List[List[State]] = []
    stack = [SearchNode(start_state, [start_state])]
    visited_in_path: Set[State] = set()  # Track visited states in current path

    while stack:
        if max_paths is not None and len(paths) >= max_paths:
            break
        node = stack.pop()
        current_state = node.state
        depth = len(node.path) - 1

        # Check depth limit
        if depth >= max_depth:
            continue

        # Check if state already in current path (avoid cycles)
        if current_state in visited_in_path:
            continue

        visited_in_path.add(current_state)

        # Check if we reached a goal
        if goal_test(current_state):
            paths.append(node.path)
            visited_in_path.remove(current_state)
            continue

        # Explore neighbors (reverse order for consistent behavior)
        neighbors = graph.get_neighbors(current_state)
        for neighbor in reversed(neighbors):
            new_path = node.path + [neighbor]
            stack.append(SearchNode(neighbor, new_path))

        # Backtrack: remove from visited when done exploring
        visited_in_path.remove(current_state)

    return paths


def heuristic_time_to_failure(
    state: State,
    graph: Graph,
    failure_states: Set[State]
) -> float:
    """
    Heuristic: Estimate time to failure based on distance to nearest failure state.
    
    This is a simple heuristic that returns a constant estimate.
    More sophisticated versions could use actual time differences from records.
    """
    if state in failure_states:
        return 0.0
    # Simple estimate: assume failure is some distance away
    return 1.0


def heuristic_sensor_distance(
    state: State,
    graph: Graph,
    failure_states: Set[State]
) -> float:
    """
    Heuristic: Estimate distance in sensor space to failure states.
    
    This compares the sensor bin values to find the closest failure state.
    """
    if state in failure_states:
        return 0.0
    
    if not failure_states:
        return 10.0  # Large value if no failure states
    
    # Simple distance: count of different bin values
    min_distance = float('inf')
    for failure_state in failure_states:
        if failure_state.machine_id != state.machine_id:
            continue
        # Count differences in sensor bins
        distance = sum(
            1 for s1, s2 in zip(state.sensor_bins, failure_state.sensor_bins)
            if s1 != s2
        )
        min_distance = min(min_distance, distance)
    
    return min_distance if min_distance != float('inf') else 10.0


def a_star(
    graph: Graph,
    start_state: State,
    goal_test: Callable[[State], bool],
    heuristic: Callable[[State, Graph, Set[State]], float],
    max_depth: int = 50,
    weight: float = 1.0
) -> Optional[List[State]]:
    """
    A* search to find optimal path from start to goal.
    
    Args:
        graph: The state graph to search
        start_state: Starting state
        goal_test: Function that returns True for goal states
        heuristic: Heuristic function(state, graph, failure_states) -> float
        max_depth: Maximum depth to search
        weight: Weight for heuristic (1.0 = standard A*, >1.0 = more greedy)
    
    Returns:
        Optimal path (list of states) or None if no path found
    """
    failure_states = graph.failure_states
    
    # Priority queue: (total_cost, node)
    open_set = []
    heapq.heappush(open_set, SearchNode(start_state, [start_state]))
    
    # Track best cost to reach each state
    g_score: Dict[State, float] = {start_state: 0.0}
    visited: Set[State] = set()
    
    while open_set:
        node = heapq.heappop(open_set)
        current_state = node.state
        
        # Skip if already visited with better cost
        if current_state in visited:
            continue
        
        visited.add(current_state)
        
        # Check depth limit
        if len(node.path) - 1 >= max_depth:
            continue
        
        # Check if we reached a goal
        if goal_test(current_state):
            return node.path
        
        # Explore neighbors
        for neighbor in graph.get_neighbors(current_state):
            if neighbor in visited:
                continue
            
            # Calculate cost (step cost = 1)
            tentative_g = g_score[current_state] + 1.0
            
            # Update if this is a better path
            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                g_score[neighbor] = tentative_g
                h = heuristic(neighbor, graph, failure_states) * weight
                new_path = node.path + [neighbor]
                new_node = SearchNode(neighbor, new_path, tentative_g, h)
                heapq.heappush(open_set, new_node)
    
    return None  # No path found


def discover_failure_sequences(
    graph: Graph,
    search_params: SearchParams
) -> List[List[State]]:
    """
    Discover sequences that lead to failures using BFS, DFS, and A*.

    Uses all three search strategies: BFS and DFS for path enumeration,
    A* with the configured heuristic for informed optimal paths.

    Args:
        graph: The state graph
        search_params: Search parameters (max_depth, heuristic, a_star_weight)

    Returns:
        List of sequences (paths) that lead to failure states
    """
    sequences: List[List[State]] = []
    if not graph.nodes:
        return sequences

    def goal_test(state: State) -> bool:
        return graph.is_failure_state(state)

    # Collect start states (neighbors of failure states, or random non-failure)
    start_states = set()
    for failure_state in graph.failure_states:
        neighbors = graph.get_neighbors(failure_state)
        for neighbor in neighbors:
            if not graph.is_failure_state(neighbor):
                start_states.add(neighbor)
    if not start_states:
        import random
        non_failure_states = [s for s in graph.nodes if not graph.is_failure_state(s)]
        start_states = set(random.sample(non_failure_states, min(100, len(non_failure_states))))

    start_states_list = list(start_states)
    max_depth = min(search_params.max_depth, 10)

    # Resolve heuristic function from config ("frequency" -> time_to_failure)
    heuristic_name = getattr(search_params, "heuristic", "time_to_failure")
    if heuristic_name == "sensor_distance":
        heuristic_fn = heuristic_sensor_distance
    else:
        heuristic_fn = heuristic_time_to_failure

    # 1. BFS: enumerate paths from each start
    for start_state in start_states_list:
        if len(sequences) >= DEFAULT_MAX_TOTAL_PATHS:
            break
        paths = bfs(
            graph,
            start_state,
            goal_test,
            max_depth=max_depth,
            max_paths=DEFAULT_MAX_PATHS_PER_START
        )
        sequences.extend(paths)

    # 2. DFS: add more paths (capped per start to balance diversity)
    dfs_max_per_start = 5
    for start_state in start_states_list:
        if len(sequences) >= DEFAULT_MAX_TOTAL_PATHS:
            break
        paths = dfs(
            graph,
            start_state,
            goal_test,
            max_depth=max_depth,
            max_paths=dfs_max_per_start
        )
        sequences.extend(paths)

    # 3. A*: add optimal path from a subset of starts (informed search)
    a_star_weight = getattr(search_params, "a_star_weight", 1.0)
    num_a_star_starts = min(15, len(start_states_list))
    for i in range(num_a_star_starts):
        if len(sequences) >= DEFAULT_MAX_TOTAL_PATHS:
            break
        start_state = start_states_list[i]
        path = a_star(
            graph,
            start_state,
            goal_test,
            heuristic_fn,
            max_depth=max_depth,
            weight=a_star_weight
        )
        if path is not None and path not in sequences:
            sequences.append(path)

    return sequences
