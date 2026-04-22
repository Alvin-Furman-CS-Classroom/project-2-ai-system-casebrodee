"""Tabular Q-learning with epsilon-greedy exploration."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, MutableMapping, Sequence, Tuple

from .loader import JsonMDP, Module6Config
from .mdp import sample_step

GREEDY_Q_TIE_EPSILON = 1e-12
"""Treat Q-values within this absolute tolerance as tied when picking greedy actions."""


def epsilon_at_episode(episode_index: int, cfg: Module6Config) -> float:
    """
    Linear decay from epsilon_start to epsilon_end over epsilon_decay_episodes.

    Args:
        episode_index: Zero-based episode index.
        cfg: Training configuration (epsilon_* and decay length).

    Returns:
        Exploration rate for this episode.
    """
    if cfg.epsilon_decay_episodes <= 0:
        return cfg.epsilon_end
    if episode_index >= cfg.epsilon_decay_episodes:
        return cfg.epsilon_end
    t = episode_index / float(cfg.epsilon_decay_episodes)
    return cfg.epsilon_start + t * (cfg.epsilon_end - cfg.epsilon_start)


def _max_q_for_state(q: Mapping[Tuple[str, str], float], state: str, actions: Sequence[str]) -> float:
    """
    Maximum Q(state, a) over actions (0.0 if no entries yet).

    Args:
        q: Flat Q-table mapping (state, action) -> value.
        state: Current MDP state label.
        actions: Legal action ids for this MDP.

    Returns:
        max_a Q(state, a).
    """
    return max((q.get((state, a), 0.0) for a in actions), default=0.0)


def greedy_action(
    q: Mapping[Tuple[str, str], float],
    state: str,
    actions: Sequence[str],
    rng: random.Random,
) -> str:
    """
    Break ties among maximal-Q actions uniformly at random.

    Args:
        q: Q-table.
        state: Current state.
        actions: Legal actions.
        rng: Random source for tie-breaking.

    Returns:
        An action achieving max Q(state, ·) within :data:`GREEDY_Q_TIE_EPSILON`.
    """
    best = max((q.get((state, a), 0.0) for a in actions), default=0.0)
    candidates = [a for a in actions if q.get((state, a), 0.0) >= best - GREEDY_Q_TIE_EPSILON]
    return rng.choice(candidates)


def epsilon_greedy_action(
    q: Mapping[Tuple[str, str], float],
    state: str,
    actions: Sequence[str],
    epsilon: float,
    rng: random.Random,
) -> str:
    """
    With probability epsilon explore uniformly; otherwise greedy.

    Args:
        q: Q-table.
        state: Current state.
        actions: Legal actions.
        epsilon: Exploration probability in [0, 1].
        rng: Random source.

    Returns:
        Chosen action id.
    """
    if rng.random() < epsilon:
        return rng.choice(list(actions))
    return greedy_action(q, state, actions, rng)


def q_learning_update(
    q: MutableMapping[Tuple[str, str], float],
    state: str,
    action: str,
    reward: float,
    next_state: str,
    mdp: JsonMDP,
    gamma: float,
    alpha: float,
) -> None:
    """
    One-step tabular Q-learning backup in place.

    Args:
        q: Q-table to update.
        state: State before the transition.
        action: Action taken.
        reward: Observed reward.
        next_state: State after the transition.
        mdp: MDP (for listing actions at next_state).
        gamma: Discount factor.
        alpha: Learning rate.
    """
    key = (state, action)
    old = q.get(key, 0.0)
    next_max = _max_q_for_state(q, next_state, mdp.actions)
    target = reward + gamma * next_max
    q[key] = old + alpha * (target - old)


@dataclass
class EpisodeRecord:
    """One training episode summary."""

    episode: int
    return_sum: float
    steps: int
    epsilon: float


def sample_initial_state(
    rng: random.Random,
    mdp: JsonMDP,
    equipment_buckets: Sequence[str],
) -> str:
    """
    Sample the start state for one simulated episode.

    If ``equipment_buckets`` is non-empty, picks a random bucket (one global Q-table,
    many machines). Otherwise samples from ``mdp.initial_state_weights``.

    Args:
        rng: Random source.
        mdp: MDP (for initial_state_weights fallback).
        equipment_buckets: Risk bucket label per equipment from diagnosis.

    Returns:
        Initial MDP state string.

    Raises:
        ValueError: If buckets are empty and ``initial_state_weights`` is missing.
    """
    if equipment_buckets:
        return rng.choice(list(equipment_buckets))
    wmap = mdp.initial_state_weights
    if not wmap:
        raise ValueError("equipment_buckets empty and mdp has no initial_state_weights")
    states = list(wmap.keys())
    weights = [wmap[s] for s in states]
    return rng.choices(states, weights=weights, k=1)[0]


def train_q_learning(
    mdp: JsonMDP,
    cfg: Module6Config,
    equipment_buckets: Sequence[str],
    rng: random.Random,
) -> Tuple[Dict[Tuple[str, str], float], List[EpisodeRecord]]:
    """
    Run tabular Q-learning for cfg.num_episodes simulated episodes.

    Args:
        mdp: Transition dynamics and reward distributions.
        cfg: Hyperparameters (gamma, alpha, epsilon schedule, horizon).
        equipment_buckets: Per-equipment risk buckets (may be empty if MDP defines initial weights).
        rng: Random source for transitions and exploration.

    Returns:
        Tuple of (learned Q-table, per-episode records).
    """
    q: Dict[Tuple[str, str], float] = {}
    history: List[EpisodeRecord] = []

    for ep in range(cfg.num_episodes):
        eps = epsilon_at_episode(ep, cfg)
        state = sample_initial_state(rng, mdp, equipment_buckets)
        total_r = 0.0
        for _ in range(cfg.max_steps_per_episode):
            action = epsilon_greedy_action(q, state, mdp.actions, eps, rng)
            next_state, reward = sample_step(rng, mdp, state, action)
            q_learning_update(q, state, action, reward, next_state, mdp, cfg.gamma, cfg.alpha)
            total_r += reward
            state = next_state
        history.append(EpisodeRecord(episode=ep, return_sum=total_r, steps=cfg.max_steps_per_episode, epsilon=eps))

    return q, history


def greedy_policy_from_q(q: Mapping[Tuple[str, str], float], mdp: JsonMDP, rng: random.Random) -> Dict[str, str]:
    """
    Extract a deterministic (up to tie-break) greedy policy for all states.

    Args:
        q: Learned Q-table.
        mdp: MDP state and action sets.
        rng: Tie-breaking random source.

    Returns:
        Map state -> action id.
    """
    return {s: greedy_action(q, s, mdp.actions, rng) for s in mdp.states}


def evaluate_fixed_policy(
    mdp: JsonMDP,
    cfg: Module6Config,
    equipment_buckets: Sequence[str],
    rng: random.Random,
    choose_action: Callable[[str, random.Random], str],
    num_episodes: int,
) -> Tuple[float, float]:
    """
    Monte Carlo mean return for a fixed policy.

    Args:
        mdp: MDP dynamics.
        cfg: Uses max_steps_per_episode as rollout horizon.
        equipment_buckets: Initial-state sampling (same as training).
        rng: Random source for transitions and initial states.
        choose_action: Callable ``(state, rng) -> action_id``.
        num_episodes: Number of rollouts.

    Returns:
        Tuple of (mean episode return, population standard deviation of returns).
    """
    returns: List[float] = []
    for _ in range(num_episodes):
        state = sample_initial_state(rng, mdp, equipment_buckets)
        total_r = 0.0
        for _ in range(cfg.max_steps_per_episode):
            a = choose_action(state, rng)
            next_state, reward = sample_step(rng, mdp, state, a)
            total_r += reward
            state = next_state
        returns.append(total_r)
    mean = sum(returns) / len(returns) if returns else 0.0
    var = sum((r - mean) ** 2 for r in returns) / len(returns) if returns else 0.0
    return mean, var**0.5
