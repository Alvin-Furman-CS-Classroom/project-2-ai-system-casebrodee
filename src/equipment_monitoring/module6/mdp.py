"""JSON-defined MDP: sample next state and reward."""

from __future__ import annotations

import random
from typing import Tuple

from .loader import JsonMDP


def sample_step(rng: random.Random, mdp: JsonMDP, state: str, action: str) -> Tuple[str, float]:
    """
    Sample the next state and reward from P(· | state, action).

    Args:
        rng: Random source (``random()`` in [0, 1)).
        mdp: Loaded MDP.
        state: Current state label.
        action: Action label.

    Returns:
        Tuple ``(next_state, reward)``.
    """
    outcomes = mdp.transitions[state][action]
    u = rng.random()
    acc = 0.0
    for o in outcomes:
        acc += o.probability
        if u < acc or o is outcomes[-1]:
            return o.next_state, o.reward
    return outcomes[-1].next_state, outcomes[-1].reward
