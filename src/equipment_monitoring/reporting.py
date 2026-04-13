"""Static HTML reporting for module outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


def _read_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.exists():
        return None, f"Missing file: {path}"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON in {path}: {exc}"


def _read_jsonl(path: Path) -> tuple[List[Dict[str, Any]] | None, str | None]:
    if not path.exists():
        return None, f"Missing file: {path}"
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows, None
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSONL in {path}: {exc}"


def infer_outputs_root(output_dir: Path, module_number: int) -> Path:
    name = output_dir.name.lower()
    expected = f"module{module_number}"
    if name == expected:
        return output_dir.parent
    return output_dir


def _status_badge(text: str) -> str:
    color = "#2a9d8f" if text == "normal" else "#e76f51"
    return f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px">{escape(text)}</span>'


def _module6_state_gloss(
    state: str,
    *,
    rich: bool,
    m1_alert: Optional[Mapping[str, Any]],
) -> str:
    """
    One-line human explanation for an MDP state key in the HTML report.

    Rich states use *_m1hot vs plain risk_*; thresholds come from rl_policy meta.m1_alert when present.
    """
    s = str(state)
    if not rich:
        if s == "risk_low":
            return "Low diagnosis risk band (Module 3 score below the first risk threshold)."
        if s == "risk_mid":
            return "Medium diagnosis risk band (between the two risk thresholds)."
        if s == "risk_high":
            return "High diagnosis risk band (at or above the second risk threshold)."
        return "MDP state from mdp.json (not one of the three default risk bands)."

    band_label = {"risk_low": "Low", "risk_mid": "Medium", "risk_high": "High"}
    hot = s.endswith("_m1hot")
    base = s[: -len("_m1hot")] if hot else s
    label = band_label.get(base, base.replace("_", " "))

    if hot:
        if isinstance(m1_alert, dict):
            ar = m1_alert.get("anomaly_rate_threshold")
            cf = m1_alert.get("confidence_fallback_threshold")
            detail = (
                f"M1-hot when Module 1 anomaly rate ≥ {ar} for that equipment (if classifications are used), "
                f"else when diagnosis meta.m1_max_confidence ≥ {cf}."
            )
            return f"{label} diagnosis risk; {detail}"
        return f"{label} diagnosis risk; M1-hot (elevated Module 1 style signal per runner rules)."

    return f"{label} diagnosis risk; plain band (Module 1 signal did not meet the M1-hot threshold)."


def load_module_outputs(outputs_root: Path) -> Dict[str, Any]:
    module1_rows, m1_err = _read_jsonl(outputs_root / "module1" / "classifications.jsonl")
    module2_sequences, m2_seq_err = _read_json(outputs_root / "module2" / "sequences.json")
    module2_warnings, m2_warn_err = _read_json(outputs_root / "module2" / "warning_signs.json")
    module3_diag, m3_err = _read_json(outputs_root / "module3" / "diagnosis.json")
    module4_plan, m4_err = _read_json(outputs_root / "module4" / "maintenance_plan.json")
    module6_policy, m6_err = _read_json(outputs_root / "module6" / "rl_policy.json")
    module6_metrics, m6m_err = _read_json(outputs_root / "module6" / "rl_metrics.json")

    errors_core = [e for e in [m1_err, m2_seq_err, m2_warn_err, m3_err] if e]
    errors_optional = [e for e in [m4_err, m6_err, m6m_err] if e]

    return {
        "module1_rows": module1_rows or [],
        "module2_sequences": (module2_sequences or {}).get("sequences", []),
        "module2_warning_signs": (module2_warnings or {}).get("warning_signs", []),
        "module3_equipment": (module3_diag or {}).get("equipment", []),
        "module4_assignments": (module4_plan or {}).get("assignments", []),
        "module4_totals": (module4_plan or {}).get("totals", {}),
        "module6_policy": (module6_policy or {}).get("policy") or {},
        "module6_q_meta": (module6_policy or {}).get("meta") or {},
        "module6_metrics": module6_metrics or {},
        "errors": errors_core + errors_optional,
        "errors_core": errors_core,
        "errors_optional": errors_optional,
        "outputs_root": str(outputs_root),
    }


def build_report_context(data: Dict[str, Any]) -> Dict[str, Any]:
    m1_rows = data["module1_rows"]
    anomalies = [r for r in m1_rows if r.get("status") == "anomaly"]

    rule_counts: Dict[str, int] = {}
    for row in anomalies:
        for rule in row.get("violated_rules", []):
            rule_counts[rule] = rule_counts.get(rule, 0) + 1

    top_rules = sorted(rule_counts.items(), key=lambda item: item[1], reverse=True)[:10]
    top_sequences = sorted(
        data["module2_sequences"],
        key=lambda row: row.get("frequency", 0),
        reverse=True,
    )[:10]
    top_warning_signs = sorted(
        data["module2_warning_signs"],
        key=lambda row: row.get("predictive_score", 0.0),
        reverse=True,
    )[:10]
    m4_assignments = data["module4_assignments"]
    action_counts: Dict[str, int] = {}
    for row in m4_assignments:
        action = str(row.get("action_id", "unknown"))
        action_counts[action] = action_counts.get(action, 0) + 1

    m6_policy = data.get("module6_policy") or {}
    m6_action_counts: Dict[str, int] = {}
    if isinstance(m6_policy, dict):
        for _state, act in m6_policy.items():
            a = str(act)
            m6_action_counts[a] = m6_action_counts.get(a, 0) + 1

    m6_metrics = data.get("module6_metrics") or {}
    trained = m6_metrics.get("trained_policy_last_window") or {}
    m6_mean_ret = trained.get("mean_return")

    m6_meta = data.get("module6_q_meta") or {}
    m6_mdp_n = (m6_metrics.get("mdp") or {}).get("num_states")
    m6_rich_states = bool(m6_meta.get("m1_alert")) or (
        isinstance(m6_policy, dict) and any(str(k).endswith("_m1hot") for k in m6_policy)
    )
    if isinstance(m6_mdp_n, int) and m6_mdp_n > 3:
        m6_rich_states = True
    m6_training_note = m6_meta.get("training_note")
    if not isinstance(m6_training_note, str):
        m6_training_note = None

    return {
        **data,
        "m1_total": len(m1_rows),
        "m1_anomalies": len(anomalies),
        "m1_anomaly_rate": (len(anomalies) / len(m1_rows) * 100.0) if m1_rows else 0.0,
        "m1_top_rules": top_rules,
        "m2_top_sequences": top_sequences,
        "m2_top_warning_signs": top_warning_signs,
        "m2_sequence_count": len(data["module2_sequences"]),
        "m2_warning_count": len(data["module2_warning_signs"]),
        "m3_equipment_count": len(data["module3_equipment"]),
        "m4_action_counts": action_counts,
        "m4_total_assignments": len(m4_assignments),
        "m6_policy_state_count": len(m6_policy) if isinstance(m6_policy, dict) else 0,
        "m6_action_counts": m6_action_counts,
        "m6_mean_return_window": m6_mean_ret,
        "m6_rich_states": m6_rich_states,
        "m6_training_note": m6_training_note,
        "m6_m1_alert_meta": m6_meta.get("m1_alert") if isinstance(m6_meta.get("m1_alert"), dict) else None,
    }


def render_report_html(context: Dict[str, Any]) -> str:
    m6_blueprint_body = """
        <p><strong>Input:</strong> per-equipment risk from <code>diagnosis.json</code> (same bucketing rule as Module 4), optionally crossed with a Module 1 &ldquo;alert&rdquo; signal from <code>classifications.jsonl</code> anomaly rate or diagnosis <code>meta.m1_max_confidence</code>; plus <code>mdp.json</code> (a <em>toy</em> stochastic world: next risk level and cost after each action)</p>
        <p><strong>Processing:</strong> Q-learning runs many episodes; each episode picks a random fleet unit, starts in that unit&rsquo;s derived MDP state, and rolls the simulator for several steps</p>
        <p><strong>Output:</strong> <code>rl_policy.json</code> (greedy action per state), <code>rl_training.json</code> (per-episode return and ε schedule), <code>rl_metrics.json</code> (trained policy vs always-defer and random baselines)</p>
        <p><strong>Note:</strong> no neural nets or Module 5—tabular RL over explicit JSON dynamics. A 3-state-only MDP (risk bands only) is still supported if <code>mdp.json</code> defines only <code>risk_low</code> / <code>risk_mid</code> / <code>risk_high</code>.</p>
"""
    module_blueprints = f"""
    <div class="blueprint-grid">
      <div class="blueprint-card">
        <h3>Module 1 blueprint</h3>
        <p><strong>Input:</strong> sensor readings + threshold config</p>
        <p><strong>Processing:</strong> rule checks classify each row as normal or anomaly</p>
        <p><strong>Output:</strong> `classifications.jsonl` + alerts</p>
        <p><strong>Feeds into:</strong> Module 2 pattern mining and Module 3 fact extraction</p>
      </div>
      <div class="blueprint-card">
        <h3>Module 2 blueprint</h3>
        <p><strong>Input:</strong> time-ordered records (+ optional Module 1 labels)</p>
        <p><strong>Processing:</strong> graph search (BFS/DFS/A*) to find pre-failure paths</p>
        <p><strong>Output:</strong> `sequences.json` + `warning_signs.json`</p>
        <p><strong>Feeds into:</strong> Module 3 diagnostic inference</p>
      </div>
      <div class="blueprint-card">
        <h3>Module 3 blueprint</h3>
        <p><strong>Input:</strong> KB rules + Module 1/2 artifacts</p>
        <p><strong>Processing:</strong> inference builds ranked hypotheses and inspections</p>
        <p><strong>Output:</strong> `diagnosis.json` with per-equipment scores</p>
        <p><strong>Feeds into:</strong> Module 4 maintenance optimization</p>
      </div>
      <div class="blueprint-card">
        <h3>Module 4 blueprint</h3>
        <p><strong>Input:</strong> diagnosis risks + action/cost constraints (+ optional production cap)</p>
        <p><strong>Processing:</strong> greedy seed, hill climbing, simulated annealing, contingency analysis</p>
        <p><strong>Output:</strong> `maintenance_plan.json` with actions, totals, and strategic summaries</p>
        <p><strong>Feeds into:</strong> operational planning; Module 6 can reuse the same action vocabulary</p>
      </div>
      <div class="blueprint-card">
        <h3>Module 6 blueprint</h3>
{m6_blueprint_body}
      </div>
    </div>
    """

    m1_rows_html = "\n".join(
        (
            "<tr>"
            f"<td>{escape(str(row.get('timestamp', '')))}</td>"
            f"<td>{escape(str(row.get('equipment_id', '')))}</td>"
            f"<td>{_status_badge(str(row.get('status', '')))}</td>"
            f"<td>{escape(', '.join(row.get('violated_rules', [])))}</td>"
            f"<td>{escape(str(round(float(row.get('confidence', 0.0)), 3)))}</td>"
            "</tr>"
        )
        for row in context["module1_rows"][:50]
    ) or "<tr><td colspan='5'>No Module 1 data yet.</td></tr>"

    rule_rows_html = "\n".join(
        f"<tr><td>{escape(rule)}</td><td>{count}</td></tr>"
        for rule, count in context["m1_top_rules"]
    ) or "<tr><td colspan='2'>No anomaly rules found.</td></tr>"

    seq_rows_html = "\n".join(
        (
            "<tr>"
            f"<td>{escape(' -> '.join(seq.get('sequence', [])))}</td>"
            f"<td>{seq.get('frequency', 0)}</td>"
            f"<td>{seq.get('avg_time_to_failure', 0.0)}</td>"
            "</tr>"
        )
        for seq in context["m2_top_sequences"]
    ) or "<tr><td colspan='3'>No Module 2 sequences yet.</td></tr>"

    warn_rows_html = "\n".join(
        (
            "<tr>"
            f"<td>{escape(str(w.get('pattern', '')))}</td>"
            f"<td>{w.get('predictive_score', 0.0)}</td>"
            f"<td>{w.get('frequency', 0)}</td>"
            f"<td>{w.get('false_positive_rate', 0.0)}</td>"
            "</tr>"
        )
        for w in context["m2_top_warning_signs"]
    ) or "<tr><td colspan='4'>No warning signs yet.</td></tr>"

    diagnosis_cards = "\n".join(
        (
            f"<details><summary><strong>{escape(str(eq.get('equipment_id', 'unknown')))}</strong> "
            f"({len(eq.get('diagnoses', []))} diagnoses)</summary>"
            "<ul>"
            + "".join(
                (
                    "<li>"
                    f"<strong>{escape(str(d.get('hypothesis', '')))}</strong> "
                    f"(score={d.get('score', 0.0)}) - {escape(str(d.get('inspection', '')))}"
                    "</li>"
                )
                for d in eq.get("diagnoses", [])
            )
            + "</ul></details>"
        )
        for eq in context["module3_equipment"]
    ) or "<p>No Module 3 diagnosis data yet.</p>"

    module6_section = ""
    if context.get("m6_policy_state_count", 0):
        m6_rich = bool(context.get("m6_rich_states"))
        m6_n = int(context.get("m6_policy_state_count", 0))
        m6_mix = " | ".join(
            f"{escape(action)}: {count}"
            for action, count in sorted(context.get("m6_action_counts", {}).items())
        )
        m6_ret = context.get("m6_mean_return_window")
        ret_line = ""
        if m6_ret is not None:
            ret_line = f"""<p><strong>Recent training score (mean return, last window of training episodes):</strong> {escape(str(m6_ret))}</p>
  <p class="subtle">Each episode rolls the toy MDP for several steps; per-step rewards are usually negative (costs), so episode return is negative. <strong>Less negative (closer to zero) is better,</strong> but the raw size depends only on how large rewards are in <code>mdp.json</code>—it is not a grade out of 100. Compare this mean to <code>baseline_always_defer</code> and <code>baseline_random</code> in <code>module6/rl_metrics.json</code>; beating both means the learned policy is doing well on this simulator. Full learning curve: per-episode return, ε-greedy ε, and running mean → <code>module6/rl_training.json</code>.</p>"""
        tn = context.get("m6_training_note")
        training_narrative = ""
        if isinstance(tn, str) and tn.strip():
            training_narrative = f"""  <div class="howto">
    <p><strong>What RL is training on:</strong> {escape(tn)}</p>
  </div>
"""
        m1a = context.get("m6_m1_alert_meta")
        m1_extra = ""
        if m6_rich and isinstance(m1a, dict):
            cp = m1a.get("classifications_path")
            ar = m1a.get("anomaly_rate_threshold")
            cf = m1a.get("confidence_fallback_threshold")
            m1_extra = f"""  <p class="subtle"><strong>M1-hot signal (this run):</strong> anomaly-rate threshold {escape(str(ar))} when classifications are available; otherwise fallback on diagnosis <code>meta.m1_max_confidence</code> ≥ {escape(str(cf))}. Classifications file: {escape(str(cp) if cp else "none (config/CLI)")}.</p>
"""
        if m6_rich:
            intro = (
                "Module 6 runs tabular Q-learning on <code>mdp.json</code>. States combine a diagnosis risk band "
                "(<code>risk_low</code>, <code>risk_mid</code>, <code>risk_high</code>) with whether Module 1 style "
                "evidence is &ldquo;hot&rdquo; (<code>_m1hot</code> suffix), so the policy can treat, for example, "
                "<code>risk_mid</code> differently from <code>risk_mid_m1hot</code>."
            )
            howto_read = (
                "<p><strong>Reading the table:</strong> Each row is one MDP state key. The suffix <code>_m1hot</code> "
                "means the run marked elevated Module 1 activity for that risk level. The action is what the agent "
                "would pick <em>in the simulator</em> after training (defer / inspect / repair — same ids as Module 4).</p>"
            )
            state_th = "MDP state (diagnosis risk × M1 signal)"
            gloss_th = "What this state means"
            summary_hint = f"(action counts summed over all {m6_n} learned states)"
        else:
            intro = (
                "Module 6 runs Q-learning in a toy simulator (<code>mdp.json</code>) to pick defer, inspect, or repair "
                "for each coarse fleet risk band from diagnosis."
            )
            howto_read = (
                "<p><strong>Reading the table:</strong> Each row is one coarse risk band. The action is the one the agent "
                "would pick <em>in the simulator</em> after training. Action names match Module 4.</p>"
            )
            state_th = "Fleet risk band (from diagnosis)"
            gloss_th = "What this state means"
            summary_hint = "(counts how many bands pick defer, inspect, or repair)"
        policy_items = context.get("module6_policy") or {}
        m1_for_gloss = context.get("m6_m1_alert_meta") if m6_rich else None
        if not isinstance(m1_for_gloss, dict):
            m1_for_gloss = None
        pol_rows = "\n".join(
            (
                "<tr>"
                f"<td><code>{escape(str(st))}</code></td>"
                f"<td class=\"subtle\">{escape(_module6_state_gloss(str(st), rich=m6_rich, m1_alert=m1_for_gloss))}</td>"
                f"<td><code>{escape(str(ac))}</code></td>"
                "</tr>"
            )
            for st, ac in sorted(policy_items.items())
        ) or "<tr><td colspan='3'>No policy rows.</td></tr>"
        m4_compare = (
            "If Module 4 assigns <code>repair</code> to specific machines while Module 6 prefers <code>defer</code> on "
            "<code>risk_high</code> or <code>risk_high_m1hot</code>, remember Module 4 optimizes a constrained schedule "
            "while Module 6 optimizes the toy MDP—different objectives."
            if m6_rich
            else "If Module 4 shows <code>repair</code> on specific machines while Module 6 shows <code>defer</code> for "
            "<code>risk_high</code>, call out that Module 4 optimizes a constrained schedule while Module 6 optimizes "
            "the toy MDP—different problems, both valid as coursework artifacts."
        )
        module6_section = f"""
<section id="module6">
  <h2>Module 6 — Learned maintenance policy (reinforcement learning)</h2>
  <p class="module-intro">{intro}</p>
{training_narrative}  <div class="howto">
    {howto_read}
  </div>
{m1_extra}{ret_line}
  <p><strong>Summary of learned choices:</strong> {m6_mix or "N/A"} <span class="subtle">{summary_hint}</span></p>
  <table>
    <thead><tr><th>{state_th}</th><th>{gloss_th}</th><th>Learned action (simulator)</th></tr></thead>
    <tbody>{pol_rows}</tbody>
  </table>
  <div class="connector"><strong>Compare with Module 4:</strong> {m4_compare}</div>
</section>
"""

    module4_section = ""
    if context["module4_assignments"]:
        m4_rows = "\n".join(
            (
                "<tr>"
                f"<td>{escape(str(a.get('equipment_id', '')))}</td>"
                f"<td>{escape(str(a.get('action_id', '')))}</td>"
                f"<td>{a.get('cost', 0)}</td>"
                f"<td>{a.get('downtime_hours', 0)}</td>"
                "</tr>"
            )
            for a in context["module4_assignments"]
        )
        totals = context["module4_totals"]
        m4_action_mix = " | ".join(
            f"{escape(action)}: {count}" for action, count in sorted(context["m4_action_counts"].items())
        )
        module4_section = f"""
<section id="module4">
  <h2>Module 4 - Maintenance Plan (optional)</h2>
  <p class="module-intro">This module turns Module 3 risk estimates into concrete actions that balance maintenance spend and residual failure risk under constraints.</p>
  <div class="metric-grid">
    <div class="metric-card">
      <div class="metric-label">Objective</div>
      <div class="metric-value">{escape(str(totals.get('objective', 0.0)))}</div>
      <div class="metric-help">Lower is better. This combines maintenance cost and predicted failure penalty.</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Maintenance cost</div>
      <div class="metric-value">{escape(str(totals.get('maintenance_cost', 0.0)))}</div>
      <div class="metric-help">Direct spend from selected actions.</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Failure penalty</div>
      <div class="metric-value">{escape(str(totals.get('failure_penalty', 0.0)))}</div>
      <div class="metric-help">Expected risk cost after actions are applied.</div>
    </div>
  </div>
  <p><strong>Action mix:</strong> {m4_action_mix or "No actions."}</p>
  <table>
    <thead><tr><th>Equipment</th><th>Action</th><th>Cost</th><th>Downtime (h)</th></tr></thead>
    <tbody>{m4_rows}</tbody>
  </table>
</section>
"""

    core_errs = context.get("errors_core") or []
    opt_errs = context.get("errors_optional") or []

    def _err_ul(items: List[str]) -> str:
        if not items:
            return "<li><span class=\"subtle\">None.</span></li>"
        return "\n".join(f"<li>{escape(msg)}</li>" for msg in items)

    core_block = (
        "<p><strong>Modules 1–3 (core)</strong></p>"
        "<ul>"
        f"{_err_ul(core_errs)}"
        "</ul>"
    )
    opt_block = (
        "<p><strong>Modules 4 &amp; 6 (optional)</strong> "
        "<span class=\"subtle\">— missing files here are normal if you have not run those modules.</span></p>"
        "<ul>"
        f"{_err_ul(opt_errs)}"
        "</ul>"
    )
    errors_panel = f"""<div class="warning">
  <p><strong>Data loading notes</strong></p>
  {core_block}
  {opt_block}
</div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Industrial Monitoring Report</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --panel: #ffffff;
      --border: #dde3ee;
      --text: #1f2937;
      --muted: #5f6b7a;
      --accent: #234a8f;
      --accent-soft: #e7efff;
      --ok: #2a9d8f;
      --warn: #e76f51;
      --shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
    }}
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 0; line-height: 1.45; color: var(--text); background: var(--bg); }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    h1, h2 {{ margin-top: 0; color: #12213f; }}
    h2 {{ margin-bottom: 6px; }}
    section {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin: 14px 0; box-shadow: var(--shadow); }}
    nav {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; margin: 12px 0 14px; display: flex; gap: 12px; flex-wrap: wrap; }}
    nav a {{ color: var(--accent); text-decoration: none; font-weight: 600; }}
    nav a:hover {{ text-decoration: underline; }}
    table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
    th, td {{ border: 1px solid var(--border); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f0f4fa; }}
    .subtle {{ color: var(--muted); margin-top: 4px; }}
    .warning {{ background: #fff8e1; padding: 8px; border: 1px solid #f0d98c; border-radius: 8px; }}
    .module-intro {{ color: var(--muted); margin: 4px 0 12px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 10px 0 12px; }}
    .metric-card {{ background: #f8fbff; border: 1px solid #d6e3ff; border-radius: 8px; padding: 10px; }}
    .metric-label {{ font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #52627a; font-weight: 700; }}
    .metric-value {{ font-size: 24px; font-weight: 700; color: #123f88; margin-top: 2px; }}
    .metric-help {{ font-size: 12px; color: #586983; margin-top: 6px; }}
    .flow {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 10px; }}
    .flow-box {{ background: var(--panel); border: 1px solid #bfd0f5; border-radius: 8px; padding: 8px 10px; box-shadow: 0 1px 2px rgba(35, 74, 143, 0.08); }}
    .flow-arrow {{ color: #6a7da6; font-weight: 700; }}
    .howto {{ background: var(--accent-soft); border: 1px solid #c3d5ff; border-radius: 8px; padding: 10px; margin-top: 8px; }}
    .howto p {{ margin: 6px 0; }}
    .blueprint-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; margin-top: 10px; }}
    .blueprint-card {{ border: 1px solid #d4def1; border-radius: 8px; background: #fbfcff; padding: 10px; }}
    .blueprint-card h3 {{ margin: 0 0 8px; font-size: 16px; color: #16346d; }}
    .blueprint-card p {{ margin: 5px 0; font-size: 13px; color: #30445f; }}
    .connector {{ margin-top: 8px; padding: 8px 10px; border-left: 4px solid #7aa2f7; background: #f6f9ff; color: #2b4266; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Industrial Equipment Monitoring Report</h1>
    <p class="subtle">Source root: {escape(context["outputs_root"])}</p>

    <section>
      <h2>System Overview</h2>
      <p class="module-intro">This report connects all modules so a reader can move from raw sensor observations to final maintenance actions.</p>
      <div class="metric-grid">
        <div class="metric-card"><div class="metric-label">Module 1 readings</div><div class="metric-value">{context["m1_total"]}</div><div class="metric-help">Rows classified as normal/anomaly.</div></div>
        <div class="metric-card"><div class="metric-label">Module 2 sequences</div><div class="metric-value">{context["m2_sequence_count"]}</div><div class="metric-help">Failure-path patterns discovered.</div></div>
        <div class="metric-card"><div class="metric-label">Module 3 equipment</div><div class="metric-value">{context["m3_equipment_count"]}</div><div class="metric-help">Machines with diagnosis blocks.</div></div>
        <div class="metric-card"><div class="metric-label">Module 4 assignments</div><div class="metric-value">{context["m4_total_assignments"]}</div><div class="metric-help">Final action decisions (if available).</div></div>
        <div class="metric-card"><div class="metric-label">Module 6 policy rows</div><div class="metric-value">{context.get("m6_policy_state_count", 0)}</div><div class="metric-help">{"MDP states with a greedy action after Q-learning (default mdp.json: six, risk × M1-hot)." if context.get("m6_rich_states") else "MDP states with a learned action (often three risk bands only)."}</div></div>
      </div>
      <div class="flow">
        <div class="flow-box">Module 1<br><span class="subtle">Classify readings</span></div>
        <div class="flow-arrow">-></div>
        <div class="flow-box">Module 2<br><span class="subtle">Discover warning sequences</span></div>
        <div class="flow-arrow">-></div>
        <div class="flow-box">Module 3<br><span class="subtle">Infer diagnoses</span></div>
        <div class="flow-arrow">-></div>
        <div class="flow-box">Module 4<br><span class="subtle">Optimize maintenance plan</span></div>
        <div class="flow-arrow">-></div>
        <div class="flow-box">Module 6<br><span class="subtle">Learn policy in a simulator (optional)</span></div>
      </div>
      <div class="howto">
        <p><strong>How to read this report:</strong> Start with anomaly volume (Module 1), pattern strength (Module 2), diagnosis (Module 3), then Module 4&rsquo;s per-machine plan. <strong>Module 6 (optional)</strong> is a tabular RL demo on <code>mdp.json</code>{"—states pair diagnosis risk with a Module 1 &ldquo;hot&rdquo; flag when using the default six-state MDP." if context.get("m6_rich_states") else "—usually one row per risk band when the MDP has only three states."} See that section for the policy table and training narrative.</p>
      </div>
      {module_blueprints}
    </section>

    <nav>
      <a href="#module1">Module 1</a>
      <a href="#module2">Module 2</a>
      <a href="#module3">Module 3</a>
      <a href="#module4">Module 4 (optional)</a>
      <a href="#module6">Module 6 — learned policy (optional)</a>
    </nav>
    {errors_panel}

    <section id="module1">
    <h2>Module 1 - Rule-Based Monitoring</h2>
    <p class="module-intro">Module 1 flags readings that violate thresholds. A higher anomaly rate usually means higher operational instability.</p>
    <div class="metric-grid">
      <div class="metric-card"><div class="metric-label">Total readings</div><div class="metric-value">{context["m1_total"]}</div></div>
      <div class="metric-card"><div class="metric-label">Anomalies</div><div class="metric-value">{context["m1_anomalies"]}</div></div>
      <div class="metric-card"><div class="metric-label">Anomaly rate</div><div class="metric-value">{context["m1_anomaly_rate"]:.1f}%</div></div>
    </div>
    <details open>
      <summary>Top violated rules</summary>
      <table>
        <thead><tr><th>Rule</th><th>Count</th></tr></thead>
        <tbody>{rule_rows_html}</tbody>
      </table>
    </details>
    <details>
      <summary>Recent classifications (max 50 rows)</summary>
      <table>
        <thead><tr><th>Timestamp</th><th>Equipment</th><th>Status</th><th>Violated rules</th><th>Confidence</th></tr></thead>
        <tbody>{m1_rows_html}</tbody>
      </table>
    </details>
    <div class="connector"><strong>Connection:</strong> Anomaly labels and violated-rule patterns become structured facts used by Module 2 and Module 3.</div>
    </section>

    <section id="module2">
    <h2>Module 2 - Failure Pattern Discovery</h2>
    <p class="module-intro">Module 2 searches historical transitions for recurring paths that appear before failures.</p>
    <div class="howto">
      <p><strong>Interpretation tip:</strong> prioritize sequences with high frequency and short average time-to-failure, then validate with warning-sign predictive score and false-positive rate.</p>
    </div>
    <details open>
      <summary>Top sequences</summary>
      <table>
        <thead><tr><th>Sequence</th><th>Frequency</th><th>Avg time to failure</th></tr></thead>
        <tbody>{seq_rows_html}</tbody>
      </table>
    </details>
    <details>
      <summary>Warning sign ranking</summary>
      <table>
        <thead><tr><th>Pattern</th><th>Predictive score</th><th>Frequency</th><th>False positive rate</th></tr></thead>
        <tbody>{warn_rows_html}</tbody>
      </table>
    </details>
    <div class="connector"><strong>Connection:</strong> Top warning signs and sequences are consumed by Module 3 to support or weaken diagnosis hypotheses.</div>
    </section>

    <section id="module3">
      <h2>Module 3 - Diagnosis and Recommendations</h2>
      <p class="module-intro">Module 3 combines facts and rules to produce hypotheses, confidence scores, and inspection guidance.</p>
      <div class="howto">
        <p><strong>Interpretation tip:</strong> look for repeated high-score hypotheses across machines to identify fleet-wide issues vs isolated failures.</p>
      </div>
      {diagnosis_cards}
      <div class="connector"><strong>Connection:</strong> The highest-confidence risk signals from this section directly drive Module 4 action selection and budget tradeoffs.</div>
    </section>
    {module4_section}
    {module6_section}
  </div>
</body>
</html>
"""


def write_report(html: str, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html, encoding="utf-8")


def generate_report(outputs_root: Path, report_path: Path) -> Path:
    context = build_report_context(load_module_outputs(outputs_root))
    html = render_report_html(context)
    write_report(html, report_path)
    return report_path


def generate_report_from_run(
    output_dir: Path,
    module_number: int,
    report_path: Path | None = None,
) -> Path:
    outputs_root = infer_outputs_root(output_dir, module_number)
    target = report_path if report_path else (outputs_root / "report.html")
    return generate_report(outputs_root=outputs_root, report_path=target)


def _artifact_exists(outputs_root: Path, *parts: str) -> bool:
    return (outputs_root.joinpath(*parts)).is_file()


def build_fleet_summary(outputs_root: Path) -> Dict[str, Any]:
    """
    Build a single JSON-serializable snapshot of whatever exists under ``outputs_root``.

    Intended for demos and downstream tooling; values are derived from the same
    loads as the HTML report (no re-running modules).
    """
    root = outputs_root.resolve()
    data = load_module_outputs(outputs_root)
    ctx = build_report_context(data)
    m6_metrics = data.get("module6_metrics") or {}
    trained = m6_metrics.get("trained_policy_last_window") or {}
    defer_b = m6_metrics.get("baseline_always_defer") or {}
    rand_b = m6_metrics.get("baseline_random") or {}
    m6_mdp = m6_metrics.get("mdp") or {}
    m4_totals = data.get("module4_totals") or {}

    top_rules = [{"rule": r, "count": c} for r, c in (ctx.get("m1_top_rules") or [])[:5]]

    policy = data.get("module6_policy") if isinstance(data.get("module6_policy"), dict) else {}

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "outputs_root": str(root),
        "artifacts": {
            "report_html": _artifact_exists(root, "report.html"),
            "module1_classifications_jsonl": _artifact_exists(root, "module1", "classifications.jsonl"),
            "module2_sequences_json": _artifact_exists(root, "module2", "sequences.json"),
            "module2_warning_signs_json": _artifact_exists(root, "module2", "warning_signs.json"),
            "module3_diagnosis_json": _artifact_exists(root, "module3", "diagnosis.json"),
            "module4_maintenance_plan_json": _artifact_exists(root, "module4", "maintenance_plan.json"),
            "module6_rl_policy_json": _artifact_exists(root, "module6", "rl_policy.json"),
            "module6_rl_metrics_json": _artifact_exists(root, "module6", "rl_metrics.json"),
        },
        "load_errors": {
            "core": list(data.get("errors_core") or []),
            "optional": list(data.get("errors_optional") or []),
        },
        "module1": {
            "row_count": int(ctx.get("m1_total", 0)),
            "anomaly_count": int(ctx.get("m1_anomalies", 0)),
            "anomaly_rate_pct": round(float(ctx.get("m1_anomaly_rate", 0.0)), 2),
            "top_violated_rules": top_rules,
        },
        "module2": {
            "sequence_count": int(ctx.get("m2_sequence_count", 0)),
            "warning_sign_count": int(ctx.get("m2_warning_count", 0)),
        },
        "module3": {
            "equipment_count": int(ctx.get("m3_equipment_count", 0)),
        },
        "module4": {
            "assignment_count": int(ctx.get("m4_total_assignments", 0)),
            "action_mix": dict(ctx.get("m4_action_counts") or {}),
            "totals": {
                "objective": m4_totals.get("objective"),
                "maintenance_cost": m4_totals.get("maintenance_cost"),
                "failure_penalty": m4_totals.get("failure_penalty"),
            },
        },
        "module6": {
            "policy_state_count": int(ctx.get("m6_policy_state_count", 0)),
            "rich_mdp_states": bool(ctx.get("m6_rich_states")),
            "trained_policy_last_window_mean_return": trained.get("mean_return"),
            "baseline_always_defer_mean_return": defer_b.get("mean_return"),
            "baseline_random_mean_return": rand_b.get("mean_return"),
            "mdp_num_states": m6_mdp.get("num_states"),
            "mdp_num_actions": m6_mdp.get("num_actions"),
            "policy": dict(policy) if policy else {},
            "meta_hyperparameters": (data.get("module6_q_meta") or {}).get("hyperparameters"),
        },
    }


def write_fleet_summary(outputs_root: Path, summary_path: Path | None = None) -> Path:
    """
    Write ``fleet_summary.json`` under ``outputs_root`` unless ``summary_path`` is given.

    Returns:
        Path to the written file.
    """
    payload = build_fleet_summary(outputs_root)
    target = summary_path if summary_path is not None else (outputs_root / "fleet_summary.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    return target
