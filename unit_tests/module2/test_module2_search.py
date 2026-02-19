"""Unit tests for Module 2 search algorithms (`search` module).

These tests exercise:
- BFS finding paths to goal states
- DFS finding paths to goal states
- A* search with heuristics
- Depth limits and cycle prevention
"""

import pytest

from equipment_monitoring.module2 import graph, search, config


def test_bfs_finds_path_to_goal() -> None:
    """Test BFS finds a path from start to goal state."""
    g = graph.Graph()
    
    # Create a simple chain: A -> B -> C (goal)
    state_a = graph.State("MACHINE_001", ("low", "low"))
    state_b = graph.State("MACHINE_001", ("medium", "low"))
    state_c = graph.State("MACHINE_001", ("high", "high"))
    
    g.add_edge(state_a, state_b)
    g.add_edge(state_b, state_c)
    g.mark_failure_state(state_c)
    
    def goal_test(state: graph.State) -> bool:
        return g.is_failure_state(state)
    
    paths = search.bfs(g, state_a, goal_test, max_depth=10)
    
    assert len(paths) > 0
    assert any(path[-1] == state_c for path in paths)


def test_bfs_respects_max_depth() -> None:
    """Test BFS respects max_depth limit."""
    g = graph.Graph()
    
    # Create a long chain
    states = [graph.State("MACHINE_001", (f"state_{i}",)) for i in range(10)]
    for i in range(len(states) - 1):
        g.add_edge(states[i], states[i + 1])
    g.mark_failure_state(states[-1])
    
    def goal_test(state: graph.State) -> bool:
        return g.is_failure_state(state)
    
    paths = search.bfs(g, states[0], goal_test, max_depth=5)
    
    # Should find paths but all should be within depth limit
    for path in paths:
        assert len(path) <= 6  # max_depth + 1 (including start)


def test_dfs_finds_path_to_goal() -> None:
    """Test DFS finds a path from start to goal state."""
    g = graph.Graph()
    
    state_a = graph.State("MACHINE_001", ("low", "low"))
    state_b = graph.State("MACHINE_001", ("medium", "low"))
    state_c = graph.State("MACHINE_001", ("high", "high"))
    
    g.add_edge(state_a, state_b)
    g.add_edge(state_b, state_c)
    g.mark_failure_state(state_c)
    
    def goal_test(state: graph.State) -> bool:
        return g.is_failure_state(state)
    
    paths = search.dfs(g, state_a, goal_test, max_depth=10)
    
    assert len(paths) > 0
    assert any(path[-1] == state_c for path in paths)


def test_a_star_finds_optimal_path() -> None:
    """Test A* finds a path to goal using heuristic."""
    g = graph.Graph()
    
    state_a = graph.State("MACHINE_001", ("low", "low"))
    state_b = graph.State("MACHINE_001", ("medium", "low"))
    state_c = graph.State("MACHINE_001", ("high", "high"))
    
    g.add_edge(state_a, state_b)
    g.add_edge(state_b, state_c)
    g.mark_failure_state(state_c)
    
    def goal_test(state: graph.State) -> bool:
        return g.is_failure_state(state)
    
    path = search.a_star(
        g,
        state_a,
        goal_test,
        search.heuristic_time_to_failure,
        max_depth=10
    )
    
    assert path is not None
    assert path[-1] == state_c


def test_a_star_no_path_returns_none() -> None:
    """Test A* returns None when no path exists."""
    g = graph.Graph()
    
    state_a = graph.State("MACHINE_001", ("low", "low"))
    state_b = graph.State("MACHINE_001", ("medium", "low"))
    state_c = graph.State("MACHINE_001", ("high", "high"))
    
    # No path from A to C
    g.add_edge(state_a, state_b)
    g.mark_failure_state(state_c)
    
    def goal_test(state: graph.State) -> bool:
        return g.is_failure_state(state)
    
    path = search.a_star(
        g,
        state_a,
        goal_test,
        search.heuristic_time_to_failure,
        max_depth=10
    )
    
    assert path is None
