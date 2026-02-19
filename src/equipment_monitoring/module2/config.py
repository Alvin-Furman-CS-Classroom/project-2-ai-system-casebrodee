"""
Configuration for Module 2: Graph building and search parameters.

This module defines configuration structures for:
- Discretization rules (how sensor values are binned into states)
- Search algorithm parameters (BFS, DFS, A* settings)
- Heuristic selection for A* search
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Literal, Union
import json
from pathlib import Path


@dataclass
class DiscretizationConfig:
    """
    Configuration for discretizing sensor values into states.
    
    Each sensor can have custom bin boundaries and labels.
    """
    bins: List[float]  # Bin boundaries (e.g., [0, 25, 50, 75, 100])
    labels: List[str]   # Labels for each bin (one less than bins, e.g., ["low", "medium", "high"])
    
    def get_bin(self, value: float) -> str:
        """
        Get the bin label for a given sensor value.
        
        Args:
            value: The sensor value to discretize
        
        Returns:
            The label for the bin containing this value
        
        Raises:
            ValueError: If value is outside all bins
        """
        for i in range(len(self.bins) - 1):
            if self.bins[i] <= value < self.bins[i + 1]:
                return self.labels[i]
        # Handle edge case: value >= last bin boundary
        if value >= self.bins[-1]:
            return self.labels[-1]
        # Value < first bin boundary
        raise ValueError(f"Value {value} is below minimum bin boundary {self.bins[0]}")


@dataclass
class GraphConfig:
    """
    Configuration for building the state graph from historical records.
    
    Attributes:
        discretization: Dictionary mapping sensor names to DiscretizationConfig
        state_components: List of sensor names to include in state representation
                        (e.g., ["Temperature", "Vibration_Level"] means state = (temp_bin, vib_bin))
    """
    discretization: Dict[str, DiscretizationConfig]
    state_components: List[str]
    
    @classmethod
    def from_json(cls, json_path: Union[str, Path]) -> 'GraphConfig':
        """
        Load GraphConfig from a JSON file.
        
        Expected JSON structure:
        {
          "discretization": {
            "Temperature": {
              "bins": [0, 25, 50, 75, 100],
              "labels": ["low", "medium", "high", "very_high"]
            },
            ...
          },
          "state_components": ["Temperature", "Vibration_Level", "Pressure"]
        }
        """
        json_path = Path(json_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        discretization = {
            sensor_name: DiscretizationConfig(
                bins=config['bins'],
                labels=config['labels']
            )
            for sensor_name, config in data['discretization'].items()
        }
        
        return cls(
            discretization=discretization,
            state_components=data['state_components']
        )
    
    def discretize_sensors(self, sensor_values: Dict[str, float]) -> Dict[str, str]:
        """
        Discretize a dictionary of sensor values using this config.
        
        Args:
            sensor_values: Dictionary of sensor name -> numeric value
        
        Returns:
            Dictionary of sensor name -> bin label (only for sensors in discretization config)
        """
        result = {}
        for sensor_name, config in self.discretization.items():
            if sensor_name in sensor_values:
                try:
                    result[sensor_name] = config.get_bin(sensor_values[sensor_name])
                except ValueError:
                    # Skip sensors with out-of-range values
                    continue
        return result


@dataclass
class SearchParams:
    """
    Parameters for search algorithms (BFS, DFS, A*).
    
    Attributes:
        max_depth: Maximum depth to search (prevents infinite loops)
        lookback_window: Only consider sequences within N steps before a failure
        min_pattern_length: Minimum length of a sequence to be considered a pattern
        heuristic: Heuristic function for A* search
                   Options: "time_to_failure", "sensor_distance", "frequency"
        a_star_weight: Weight for A* heuristic (1.0 = standard A*, >1.0 = more greedy)
    """
    max_depth: int = 50
    lookback_window: int = 50
    min_pattern_length: int = 3
    heuristic: Literal["time_to_failure", "sensor_distance", "frequency"] = "time_to_failure"
    a_star_weight: float = 1.0
    
    @classmethod
    def from_json(cls, json_path: Union[str, Path]) -> 'SearchParams':
        """
        Load SearchParams from a JSON file.
        
        Expected JSON structure:
        {
          "max_depth": 50,
          "lookback_window": 50,
          "min_pattern_length": 3,
          "heuristic": "time_to_failure",
          "a_star_weight": 1.0
        }
        """
        json_path = Path(json_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        return cls(
            max_depth=data.get('max_depth', 50),
            lookback_window=data.get('lookback_window', 50),
            min_pattern_length=data.get('min_pattern_length', 3),
            heuristic=data.get('heuristic', 'time_to_failure'),
            a_star_weight=data.get('a_star_weight', 1.0)
        )
