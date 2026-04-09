"""Load Module 6 config and MDP JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

PROB_SUM_EPS = 1e-5


class Module6ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TransitionOutcome:
    probability: float
    next_state: str
    reward: float


@dataclass(frozen=True)
class JsonMDP:
    """MDP dynamics from JSON: stochastic transitions per (state, action)."""

    states: Tuple[str, ...]
    actions: Tuple[str, ...]
    transitions: Mapping[str, Mapping[str, Tuple[TransitionOutcome, ...]]]
    initial_state_weights: Mapping[str, float] | None


@dataclass(frozen=True)
class Module6Config:
    gamma: float
    alpha: float
    epsilon_start: float
    epsilon_end: float
    epsilon_decay_episodes: int
    num_episodes: int
    max_steps_per_episode: int
    random_seed: int
    risk_thresholds: Tuple[float, float]
    mdp_path: Path
    module4_config_path: Path | None


def _load_json(path: Path, label: str) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise Module6ConfigError(f"{label} is not valid JSON ({path}): {e}") from e


def _resolve_path(base_dir: Path, raw: str | None, default_name: str) -> Path:
    if raw is None or raw == "":
        return base_dir / default_name
    p = Path(raw)
    if not p.is_absolute():
        return (base_dir / p).resolve()
    return p.resolve()


def load_module6_config(path: str | Path) -> Module6Config:
    """
    Load and validate Module 6 training / path configuration JSON.

    Args:
        path: Path to ``module6_config.json`` (``mdp_path`` and optional ``module4_config_path``
            are resolved relative to this file's directory unless absolute).

    Returns:
        Frozen :class:`Module6Config`.

    Raises:
        Module6ConfigError: Missing keys, invalid numeric ranges, or invalid JSON.
    """
    p = Path(path)
    base_dir = p.parent.resolve()
    data = _load_json(p, "Module 6 config")

    if not isinstance(data, dict):
        raise Module6ConfigError("Module 6 config must be a JSON object")

    try:
        gamma = float(data["gamma"])
        alpha = float(data["alpha"])
        epsilon_start = float(data["epsilon_start"])
        epsilon_end = float(data["epsilon_end"])
        epsilon_decay_episodes = int(data["epsilon_decay_episodes"])
        num_episodes = int(data["num_episodes"])
        max_steps_per_episode = int(data["max_steps_per_episode"])
        random_seed = int(data["random_seed"])
    except (KeyError, TypeError, ValueError) as e:
        raise Module6ConfigError(f"missing or invalid core training field: {e}") from e

    raw_th = data.get("risk_thresholds")
    if not isinstance(raw_th, list) or len(raw_th) != 2:
        raise Module6ConfigError("risk_thresholds must be an array of two numbers [low_mid, mid_high]")
    try:
        t0, t1 = float(raw_th[0]), float(raw_th[1])
    except (TypeError, ValueError) as e:
        raise Module6ConfigError(f"risk_thresholds must be numbers: {e}") from e
    if not (0.0 <= t0 <= t1 <= 1.0):
        raise Module6ConfigError("risk_thresholds must satisfy 0 <= t0 <= t1 <= 1")

    mdp_path = _resolve_path(base_dir, data.get("mdp_path"), "mdp.json")

    m4_raw = data.get("module4_config_path")
    module4_config_path: Path | None
    if m4_raw:
        module4_config_path = _resolve_path(base_dir, str(m4_raw), "")
    else:
        module4_config_path = None

    if not (0.0 <= gamma <= 1.0):
        raise Module6ConfigError("gamma must be in [0, 1]")
    if alpha <= 0.0 or alpha > 1.0:
        raise Module6ConfigError("alpha must be in (0, 1]")
    if not (0.0 <= epsilon_end <= epsilon_start <= 1.0):
        raise Module6ConfigError("need 0 <= epsilon_end <= epsilon_start <= 1")
    if epsilon_decay_episodes < 0:
        raise Module6ConfigError("epsilon_decay_episodes must be non-negative")
    if num_episodes < 1:
        raise Module6ConfigError("num_episodes must be at least 1")
    if max_steps_per_episode < 1:
        raise Module6ConfigError("max_steps_per_episode must be at least 1")

    return Module6Config(
        gamma=gamma,
        alpha=alpha,
        epsilon_start=epsilon_start,
        epsilon_end=epsilon_end,
        epsilon_decay_episodes=epsilon_decay_episodes,
        num_episodes=num_episodes,
        max_steps_per_episode=max_steps_per_episode,
        random_seed=random_seed,
        risk_thresholds=(t0, t1),
        mdp_path=mdp_path,
        module4_config_path=module4_config_path,
    )


def load_mdp_json(path: str | Path) -> JsonMDP:
    """
    Load a finite MDP: states, actions, stochastic transitions, optional initial weights.

    Each ``transitions[s][a]`` entry must be a list of ``[probability, next_state, reward]``
    triples whose probabilities sum to 1 (within :data:`PROB_SUM_EPS`).

    Args:
        path: Path to ``mdp.json``.

    Returns:
        Immutable :class:`JsonMDP`.

    Raises:
        Module6ConfigError: Invalid structure, unknown states, or bad probability sums.
    """
    p = Path(path)
    data = _load_json(p, "MDP file")
    if not isinstance(data, dict):
        raise Module6ConfigError("MDP must be a JSON object")

    states = data.get("states")
    actions = data.get("actions")
    trans_root = data.get("transitions")
    if not isinstance(states, list) or not states:
        raise Module6ConfigError("mdp.states must be a non-empty array")
    if not isinstance(actions, list) or not actions:
        raise Module6ConfigError("mdp.actions must be a non-empty array")
    if not isinstance(trans_root, dict):
        raise Module6ConfigError("mdp.transitions must be an object")

    state_set = [str(s) for s in states]
    action_set = [str(a) for a in actions]
    if len(set(state_set)) != len(state_set):
        raise Module6ConfigError("duplicate state in mdp.states")
    if len(set(action_set)) != len(action_set):
        raise Module6ConfigError("duplicate action in mdp.actions")

    transitions: Dict[str, Dict[str, Tuple[TransitionOutcome, ...]]] = {}

    for s in state_set:
        if s not in trans_root:
            raise Module6ConfigError(f"transitions missing state {s!r}")
        raw_s = trans_root[s]
        if not isinstance(raw_s, dict):
            raise Module6ConfigError(f"transitions[{s!r}] must be an object")
        inner: Dict[str, Tuple[TransitionOutcome, ...]] = {}
        for a in action_set:
            if a not in raw_s:
                raise Module6ConfigError(f"transitions[{s!r}] missing action {a!r}")
            raw_list = raw_s[a]
            if not isinstance(raw_list, list) or not raw_list:
                raise Module6ConfigError(f"transitions[{s!r}][{a!r}] must be a non-empty array")
            outcomes: List[TransitionOutcome] = []
            psum = 0.0
            for i, item in enumerate(raw_list):
                if not isinstance(item, (list, tuple)) or len(item) != 3:
                    raise Module6ConfigError(
                        f"transitions[{s!r}][{a!r}][{i}] must be [probability, next_state, reward]"
                    )
                prob, next_s, reward = item
                prob_f = float(prob)
                next_str = str(next_s)
                reward_f = float(reward)
                if next_str not in state_set:
                    raise Module6ConfigError(f"unknown next_state {next_str!r} from ({s!r}, {a!r})")
                if prob_f < 0.0:
                    raise Module6ConfigError(f"negative probability in ({s!r}, {a!r})")
                psum += prob_f
                outcomes.append(
                    TransitionOutcome(probability=prob_f, next_state=next_str, reward=reward_f)
                )
            if abs(psum - 1.0) > PROB_SUM_EPS:
                raise Module6ConfigError(
                    f"probabilities for ({s!r}, {a!r}) sum to {psum}, expected 1.0"
                )
            inner[a] = tuple(outcomes)
        transitions[s] = inner

    weights_raw = data.get("initial_state_weights")
    initial: Dict[str, float] | None
    if weights_raw is None:
        initial = None
    else:
        if not isinstance(weights_raw, dict):
            raise Module6ConfigError("initial_state_weights must be an object or null")
        initial = {}
        wsum = 0.0
        for k, v in weights_raw.items():
            ks = str(k)
            if ks not in state_set:
                raise Module6ConfigError(f"initial_state_weights unknown state {ks!r}")
            wf = float(v)
            if wf < 0.0:
                raise Module6ConfigError(f"initial_state_weights[{ks!r}] must be non-negative")
            wsum += wf
            initial[ks] = wf
        if abs(wsum - 1.0) > PROB_SUM_EPS:
            raise Module6ConfigError(f"initial_state_weights sum to {wsum}, expected 1.0")

    return JsonMDP(
        states=tuple(state_set),
        actions=tuple(action_set),
        transitions=transitions,
        initial_state_weights=initial,
    )


def validate_actions_against_module4(mdp: JsonMDP, module4_config_path: Path) -> None:
    """
    Ensure every MDP action id appears in the Module 4 maintenance config.

    Args:
        mdp: MDP whose ``actions`` must be a subset of Module 4 action ids.
        module4_config_path: Path to ``module4_config.json``.

    Raises:
        Module6ConfigError: If the Module 4 file is invalid or any MDP action is missing from Module 4.
    """
    from ..module4.loader import Module4ConfigError, load_module4_config

    try:
        cfg = load_module4_config(module4_config_path)
    except Module4ConfigError as e:
        raise Module6ConfigError(
            f"Cannot validate MDP actions: invalid Module 4 config ({module4_config_path}): {e}"
        ) from e
    m4_ids = {a.id for a in cfg.actions}
    mdp_ids = set(mdp.actions)
    if not mdp_ids <= m4_ids:
        missing = sorted(mdp_ids - m4_ids)
        raise Module6ConfigError(
            f"MDP actions {missing} are not present in Module 4 config actions"
        )
