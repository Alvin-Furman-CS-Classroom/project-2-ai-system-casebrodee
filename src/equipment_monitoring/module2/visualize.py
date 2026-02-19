"""
Visualization for Module 2: Plot equipment degradation over time.

This module provides optional visualization capabilities for:
- State transitions over time per machine
- Failure points marked on timelines
- Degradation patterns
"""

from typing import List, Optional, Dict
from pathlib import Path
from .graph import Graph, State
from .io import HistoricalRecord


def plot_machine_degradation(
    machine_id: str,
    records: List[HistoricalRecord],
    graph: Graph,
    output_path: Optional[Path] = None
) -> None:
    """
    Plot state transitions and failure points for a single machine.
    
    Args:
        machine_id: Machine to plot
        records: Historical records for this machine (sorted by time)
        graph: The state graph
        output_path: Optional path to save the plot (if None, plot is not saved)
    
    Note: This is a placeholder. Actual implementation will require matplotlib
    or another plotting library to be added as a dependency.
    """
    # TODO: Implement visualization using matplotlib
    # - Plot sensor values over time
    # - Mark state transitions
    # - Highlight failure points
    # - Save to output_path if provided
    pass


def plot_all_machines(
    graph: Graph,
    records_by_machine: Dict[str, List[HistoricalRecord]],
    output_dir: Path
) -> None:
    """
    Generate degradation plots for all machines.
    
    Args:
        graph: The state graph
        records_by_machine: Dictionary mapping machine_id to sorted records
        output_dir: Directory to save plot files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for machine_id, records in records_by_machine.items():
        output_path = output_dir / f"{machine_id}_degradation.png"
        plot_machine_degradation(machine_id, records, graph, output_path)
