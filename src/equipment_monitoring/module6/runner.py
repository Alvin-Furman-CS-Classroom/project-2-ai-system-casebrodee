"""Module 6 runner: diagnosis + JSON MDP -> Q-learning outputs."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .loader import JsonMDP, Module6Config, Module6ConfigError, load_mdp_json, load_module6_config, validate_actions_against_module4
from .q_learning import EpisodeRecord, evaluate_fixed_policy, greedy_policy_from_q, train_q_learning
from .state import equipment_mdp_start_states, mdp_supports_m1hot_rich_states

# --- Tunables (reported in meta / metrics; avoid magic numbers in logic below) ---

TRAINING_RETURN_TAIL_MAX_EPISODES = 500
"""Cap on how many final episodes contribute to mean/std in rl_metrics trained_policy_last_window."""

BASELINE_EVAL_EPISODES_MIN = 200
"""Minimum Monte Carlo episodes when evaluating fixed baselines."""

BASELINE_EVAL_EPISODES_MAX = 2000
"""Upper cap so baseline evaluation stays bounded when num_episodes is huge."""

RNG_STREAM_OFFSET_GREEDY_POLICY = 911
"""Offset added to training seed for a separate RNG when breaking Q-value ties in greedy policy."""

RNG_STREAM_OFFSET_BASELINES = 404
"""Offset added to training seed for baseline policy Monte Carlo evaluation."""


def _write_json(path: Path, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _prepare_mdp_and_buckets(
    diagnosis_path: str | Path,
    module6_config_path: str | Path,
    mdp_path: str | Path | None,
    module4_config_path: str | Path | None,
    classifications_path: str | Path | None,
) -> Tuple[Module6Config, JsonMDP, Path, Path | None, List[str], Path | None]:
    cfg = load_module6_config(module6_config_path)
    mdp_file = Path(mdp_path) if mdp_path else cfg.mdp_path
    mdp = load_mdp_json(mdp_file)

    m4_path = Path(module4_config_path) if module4_config_path else cfg.module4_config_path
    if m4_path is not None:
        validate_actions_against_module4(mdp, m4_path)

    cls_effective: Path | None
    if classifications_path is not None:
        cls_effective = Path(classifications_path)
    else:
        cls_effective = cfg.classifications_path

    try:
        buckets = equipment_mdp_start_states(
            diagnosis_path,
            cfg.risk_thresholds,
            mdp.states,
            classifications_path=cls_effective,
            m1_anomaly_rate_alert=cfg.m1_anomaly_rate_alert,
            m1_confidence_alert_fallback=cfg.m1_confidence_alert_fallback,
        )
    except FileNotFoundError as e:
        raise Module6ConfigError(str(e)) from e

    if not buckets and not mdp.initial_state_weights:
        raise Module6ConfigError(
            "diagnosis has no equipment rows and MDP has no initial_state_weights; cannot start episodes"
        )

    return cfg, mdp, mdp_file, m4_path, buckets, cls_effective


def _tail_return_stats(
    history: List[EpisodeRecord],
    max_window: int,
) -> Tuple[int, float, float]:
    last_n = min(max_window, len(history))
    tail = history[-last_n:]
    tail_returns = [h.return_sum for h in tail]
    if not tail_returns:
        return last_n, 0.0, 0.0
    mean_tail = sum(tail_returns) / len(tail_returns)
    var_tail = sum((x - mean_tail) ** 2 for x in tail_returns) / len(tail_returns)
    return last_n, mean_tail, var_tail**0.5


def _q_table_to_nested_dict(q: Dict[Tuple[str, str], float], mdp: JsonMDP) -> Dict[str, Dict[str, float]]:
    return {s: {a: round(q.get((s, a), 0.0), 6) for a in mdp.actions} for s in mdp.states}


def _run_baselines(
    mdp: JsonMDP,
    cfg: Module6Config,
    buckets: List[str],
    seed: int,
    num_training_episodes: int,
) -> Tuple[float, float, float, float, int]:
    if "defer" not in mdp.actions:
        raise Module6ConfigError("MDP actions must include 'defer' for baseline comparison")

    eval_rng = random.Random(seed + RNG_STREAM_OFFSET_BASELINES)

    def always_defer(_s: str, _r: random.Random) -> str:
        return "defer"

    def random_policy(_s: str, r: random.Random) -> str:
        return r.choice(list(mdp.actions))

    eval_episodes = max(
        BASELINE_EVAL_EPISODES_MIN,
        min(num_training_episodes, BASELINE_EVAL_EPISODES_MAX),
    )
    mean_defer, std_defer = evaluate_fixed_policy(
        mdp, cfg, buckets, eval_rng, always_defer, eval_episodes
    )
    mean_rand, std_rand = evaluate_fixed_policy(
        mdp, cfg, buckets, eval_rng, random_policy, eval_episodes
    )
    return mean_defer, std_defer, mean_rand, std_rand, eval_episodes


def _build_meta(
    diagnosis_path: str | Path,
    module6_config_path: str | Path,
    mdp_file: Path,
    seed: int,
    cfg: Module6Config,
    buckets: List[str],
    m4_path: Path | None,
    mdp: JsonMDP,
    classifications_effective: Path | None,
) -> Dict[str, Any]:
    rich = mdp_supports_m1hot_rich_states(mdp.states)
    if rich:
        training_note = (
            "Global Q-table over risk × Module-1-alert states (e.g. risk_mid vs risk_mid_m1hot); "
            "each episode starts from a random equipment's derived start state using diagnosis risk "
            "and classifications anomaly rate (when provided) or diagnosis meta m1_max_confidence."
        )
    else:
        training_note = (
            "Global Q-table over risk buckets; each episode starts from a random "
            "equipment's bucket from diagnosis.json."
        )

    meta: Dict[str, Any] = {
        "diagnosis_path": str(Path(diagnosis_path).resolve()),
        "module6_config_path": str(Path(module6_config_path).resolve()),
        "mdp_path": str(mdp_file.resolve()),
        "random_seed": seed,
        "module5_required": False,
        "training_note": training_note,
        "hyperparameters": {
            "gamma": cfg.gamma,
            "alpha": cfg.alpha,
            "epsilon_start": cfg.epsilon_start,
            "epsilon_end": cfg.epsilon_end,
            "epsilon_decay_episodes": cfg.epsilon_decay_episodes,
            "num_episodes": cfg.num_episodes,
            "max_steps_per_episode": cfg.max_steps_per_episode,
        },
        "equipment_count": len(buckets),
        "risk_thresholds": list(cfg.risk_thresholds),
    }
    if m4_path is not None:
        meta["module4_config_path"] = str(m4_path.resolve())
    if rich:
        meta["m1_alert"] = {
            "classifications_path": str(classifications_effective.resolve())
            if classifications_effective is not None
            else None,
            "anomaly_rate_threshold": cfg.m1_anomaly_rate_alert,
            "confidence_fallback_threshold": cfg.m1_confidence_alert_fallback,
        }
    return meta


def _write_rl_policy(
    output_dir: Path,
    policy: Dict[str, str],
    q_json: Dict[str, Dict[str, float]],
    meta: Dict[str, Any],
) -> None:
    _write_json(output_dir / "rl_policy.json", {"policy": policy, "q_table": q_json, "meta": meta})


def _write_rl_training(
    output_dir: Path,
    history: List[EpisodeRecord],
    cfg: Module6Config,
    last_n: int,
    mean_tail: float,
) -> None:
    running = 0.0
    training_rows: List[Dict[str, Any]] = []
    for i, h in enumerate(history):
        running = (running * i + h.return_sum) / (i + 1) if i > 0 else h.return_sum
        training_rows.append(
            {
                "episode": h.episode,
                "return": round(h.return_sum, 4),
                "steps": h.steps,
                "epsilon": round(h.epsilon, 6),
                "return_mean_so_far": round(running, 4),
            }
        )
    _write_json(
        output_dir / "rl_training.json",
        {
            "episodes": training_rows,
            "meta": {
                "num_episodes": cfg.num_episodes,
                "mean_return_last_window": round(mean_tail, 4),
                "window_size": last_n,
            },
        },
    )


def _write_rl_metrics(
    output_dir: Path,
    last_n: int,
    mean_tail: float,
    std_tail: float,
    mean_defer: float,
    std_defer: float,
    mean_rand: float,
    std_rand: float,
    eval_episodes: int,
    mdp: JsonMDP,
) -> None:
    _write_json(
        output_dir / "rl_metrics.json",
        {
            "trained_policy_last_window": {
                "mean_return": round(mean_tail, 4),
                "std_return": round(std_tail, 4),
                "window_episodes": last_n,
            },
            "baseline_always_defer": {
                "mean_return": round(mean_defer, 4),
                "std_return": round(std_defer, 4),
                "eval_episodes": eval_episodes,
            },
            "baseline_random": {
                "mean_return": round(mean_rand, 4),
                "std_return": round(std_rand, 4),
                "eval_episodes": eval_episodes,
            },
            "mdp": {
                "num_states": len(mdp.states),
                "num_actions": len(mdp.actions),
                "states": list(mdp.states),
                "actions": list(mdp.actions),
            },
        },
    )


def run_module6(
    diagnosis_path: str | Path,
    module6_config_path: str | Path,
    output_dir: str | Path,
    mdp_path: str | Path | None = None,
    module4_config_path: str | Path | None = None,
    classifications_path: str | Path | None = None,
    random_seed: int | None = None,
) -> None:
    """
    Train tabular Q-learning on a JSON MDP.

    **Training narrative:** One global Q-table over MDP states. With the default
    6-state MDP, each state pairs a diagnosis risk bucket (``risk_low`` /
    ``risk_mid`` / ``risk_high``) with whether Module 1 style signals are "hot"
    (``*_m1hot``), using classifications anomaly rate when a classifications file
    is configured or passed, else ``meta.m1_max_confidence`` on each equipment block.
    Each episode picks a random equipment and starts in that equipment's derived
    state, then rolls the MDP for ``max_steps_per_episode`` steps. Module 5 is not used.

    With a 3-state MDP JSON, behavior matches the original risk-bucket-only mapping.

    If diagnosis lists no equipment, initial states are drawn from
    ``initial_state_weights`` in the MDP JSON (must be present).

    Args:
        diagnosis_path: Path to Module 3 ``diagnosis.json``.
        module6_config_path: Path to Module 6 training / path config JSON.
        output_dir: Directory for ``rl_policy.json``, ``rl_training.json``, ``rl_metrics.json``.
        mdp_path: Optional override for MDP JSON (default from config).
        module4_config_path: Optional override for Module 4 config when validating actions.
        classifications_path: Optional override for Module 1 ``classifications.jsonl`` (M1-hot states).
        random_seed: Optional RNG seed override (default from config).

    Raises:
        Module6ConfigError: Invalid config, MDP, diagnosis (for structural/JSON issues),
            bucket/state mismatch, or missing initial weights when diagnosis is empty.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg, mdp, mdp_file, m4_path, buckets, cls_effective = _prepare_mdp_and_buckets(
        diagnosis_path, module6_config_path, mdp_path, module4_config_path, classifications_path
    )

    seed = int(random_seed) if random_seed is not None else cfg.random_seed
    rng = random.Random(seed)

    q, history = train_q_learning(mdp, cfg, buckets, rng)
    policy_rng = random.Random(seed + RNG_STREAM_OFFSET_GREEDY_POLICY)
    policy = greedy_policy_from_q(q, mdp, policy_rng)

    last_n, mean_tail, std_tail = _tail_return_stats(history, TRAINING_RETURN_TAIL_MAX_EPISODES)
    mean_defer, std_defer, mean_rand, std_rand, eval_episodes = _run_baselines(
        mdp, cfg, buckets, seed, cfg.num_episodes
    )

    q_json = _q_table_to_nested_dict(q, mdp)
    meta = _build_meta(
        diagnosis_path,
        module6_config_path,
        mdp_file,
        seed,
        cfg,
        buckets,
        m4_path,
        mdp,
        cls_effective,
    )

    _write_rl_policy(output_dir, policy, q_json, meta)
    _write_rl_training(output_dir, history, cfg, last_n, mean_tail)
    _write_rl_metrics(
        output_dir,
        last_n,
        mean_tail,
        std_tail,
        mean_defer,
        std_defer,
        mean_rand,
        std_rand,
        eval_episodes,
        mdp,
    )
