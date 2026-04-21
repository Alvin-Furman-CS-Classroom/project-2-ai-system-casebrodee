"""Static HTML reporting for module outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


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


def _fmt_chart_value(val: float, *, as_int: bool) -> str:
    if as_int:
        return str(int(round(val)))
    return f"{val:.2f}"


def _render_hbar_chart(
    title: str,
    rows: List[tuple[str, float]],
    *,
    as_int: bool = True,
    bar_color: str = "#3d6eb0",
    track_color: str = "#e8ecf4",
) -> str:
    """Compact inline SVG horizontal bars (no external JS)."""
    if not rows:
        return ""
    max_v = max(v for _, v in rows)
    if max_v <= 0:
        max_v = 1.0
    row_h = 20
    label_w = 188
    bar_w = 292
    gap = 5
    top_pad = 22
    h = top_pad + len(rows) * (row_h + gap) + 10
    w = label_w + bar_w + 56
    parts: List[str] = [
        '<figure class="chart-figure">',
        f"<figcaption>{escape(title)}</figcaption>",
        f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-height:{min(h, 320)}px" '
        'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{escape(title)}">',
        f'<text x="0" y="15" font-size="11" font-weight="700" fill="#12213f">{escape(title)}</text>',
    ]
    y = float(top_pad)
    for label, val in rows:
        frac = min(1.0, max(0.0, float(val) / max_v))
        bw = frac * bar_w
        lab = label if len(label) <= 34 else label[:31] + "..."
        parts.append(
            f'<text x="0" y="{y + 14:.0f}" font-size="10" fill="#374151">{escape(lab)}</text>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y:.0f}" width="{bar_w}" height="{row_h}" rx="4" fill="{track_color}"/>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y:.0f}" width="{bw:.1f}" height="{row_h}" rx="4" fill="{bar_color}"/>'
        )
        parts.append(
            f'<text x="{label_w + bar_w + 6:.0f}" y="{y + 14:.0f}" font-size="10" fill="#5f6b7a">'
            f"{escape(_fmt_chart_value(val, as_int=as_int))}</text>"
        )
        y += row_h + gap
    parts.append("</svg></figure>")
    return "\n".join(parts)


def _action_pill_html(action: str) -> str:
    a = str(action).lower()
    cls = {
        "defer": "action-defer",
        "inspect": "action-inspect",
        "repair": "action-repair",
    }.get(a, "action-unknown")
    return f'<span class="action-pill {cls}"><code>{escape(str(action))}</code></span>'


def _render_anomaly_spark(pct: float) -> str:
    """Thin bar showing anomaly share (0–100)."""
    p = max(0.0, min(100.0, float(pct)))
    return (
        f'<div class="spark-wrap" role="img" aria-label="Anomaly rate {p:.1f} percent">'
        f'<div class="spark-track"><span class="spark-fill" style="width:{p:.2f}%"></span></div>'
        f'<span class="spark-label">{p:.1f}%</span></div>'
    )


def _render_pipeline_svg() -> str:
    """Static pipeline diagram: modules as nodes, files on edges."""
    return """
<figure class="pipeline-figure">
  <figcaption>Data flow across modules</figcaption>
  <svg viewBox="0 0 720 188" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Pipeline from Module 1 through Module 6">
    <defs>
      <linearGradient id="nodeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:#f8fbff;stop-opacity:1" />
        <stop offset="100%" style="stop-color:#e7efff;stop-opacity:1" />
      </linearGradient>
      <marker id="pipeArrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
        <path d="M0,0 L7,3.5 L0,7 Z" fill="#7a8fb3"/>
      </marker>
    </defs>
    <text x="8" y="20" font-size="13" font-weight="700" fill="#12213f">End-to-end pipeline</text>
    <text x="8" y="36" font-size="10" fill="#5f6b7a">Arrows show primary artifacts consumed by the next stage.</text>
    <g transform="translate(12, 48)">
      <rect x="0" y="4" width="96" height="44" rx="8" fill="url(#nodeGrad)" stroke="#bfd0f5" stroke-width="1.2"/>
      <text x="48" y="26" text-anchor="middle" font-size="11" font-weight="700" fill="#16346d">M1</text>
      <text x="48" y="40" text-anchor="middle" font-size="8.5" fill="#5f6b7a">classify</text>
      <rect x="115" y="4" width="96" height="44" rx="8" fill="url(#nodeGrad)" stroke="#bfd0f5" stroke-width="1.2"/>
      <text x="163" y="26" text-anchor="middle" font-size="11" font-weight="700" fill="#16346d">M2</text>
      <text x="163" y="40" text-anchor="middle" font-size="8.5" fill="#5f6b7a">search</text>
      <rect x="240" y="4" width="96" height="44" rx="8" fill="url(#nodeGrad)" stroke="#bfd0f5" stroke-width="1.2"/>
      <text x="288" y="26" text-anchor="middle" font-size="11" font-weight="700" fill="#16346d">M3</text>
      <text x="288" y="40" text-anchor="middle" font-size="8.5" fill="#5f6b7a">FOL</text>
      <rect x="365" y="4" width="96" height="44" rx="8" fill="url(#nodeGrad)" stroke="#bfd0f5" stroke-width="1.2"/>
      <text x="413" y="26" text-anchor="middle" font-size="11" font-weight="700" fill="#16346d">M4</text>
      <text x="413" y="40" text-anchor="middle" font-size="8.5" fill="#5f6b7a">optimize</text>
      <rect x="490" y="4" width="96" height="44" rx="8" fill="url(#nodeGrad)" stroke="#bfd0f5" stroke-width="1.2"/>
      <text x="538" y="26" text-anchor="middle" font-size="11" font-weight="700" fill="#16346d">M6</text>
      <text x="538" y="40" text-anchor="middle" font-size="8.5" fill="#5f6b7a">RL (opt.)</text>
      <line x1="98" y1="26" x2="112" y2="26" stroke="#9aaccc" stroke-width="1.4" marker-end="url(#pipeArrow)"/>
      <line x1="223" y1="26" x2="237" y2="26" stroke="#9aaccc" stroke-width="1.4" marker-end="url(#pipeArrow)"/>
      <line x1="348" y1="26" x2="362" y2="26" stroke="#9aaccc" stroke-width="1.4" marker-end="url(#pipeArrow)"/>
      <line x1="473" y1="26" x2="487" y2="26" stroke="#9aaccc" stroke-width="1.4" marker-end="url(#pipeArrow)"/>
    </g>
    <text x="12" y="128" font-size="9.5" fill="#5f6b7a">M4 output: <tspan font-family="monospace">maintenance_plan.json</tspan> · M6 output: <tspan font-family="monospace">rl_policy.json</tspan></text>
    <text x="12" y="148" font-size="9.5" fill="#5f6b7a">Module 5 (supervised learning) is not part of this repository.</text>
  </svg>
</figure>
"""


def _render_normal_anomaly_stacked(total: int, anomalies: int) -> str:
    """Single stacked bar: normal vs anomaly share of Module 1 rows."""
    if total <= 0:
        return (
            '<figure class="stacked-fig"><figcaption>Reading mix</figcaption>'
            '<p class="subtle">No classifications to chart.</p></figure>'
        )
    normal = max(0, int(total) - int(anomalies))
    pn = 100.0 * normal / float(total)
    pa = 100.0 * float(anomalies) / float(total)
    return f"""<figure class="stacked-fig">
  <figcaption>Module 1 reading mix (normal vs anomaly)</figcaption>
  <div class="stacked-bar" role="img" aria-label="Normal {pn:.1f} percent, anomaly {pa:.1f} percent">
    <span class="seg seg-normal" style="width:{pn:.2f}%" title="{normal} normal readings ({pn:.1f}%)"></span>
    <span class="seg seg-anom" style="width:{pa:.2f}%" title="{anomalies} anomaly readings ({pa:.1f}%)"></span>
  </div>
  <div class="stacked-legend">
    <span class="lg lg-n"><span class="swatch sw-n"></span>Normal <strong>{normal}</strong> ({pn:.1f}%)</span>
    <span class="lg lg-a"><span class="swatch sw-a"></span>Anomaly <strong>{anomalies}</strong> ({pa:.1f}%)</span>
  </div>
</figure>"""


def _render_start_here_panel() -> str:
    steps: Sequence[tuple[str, str, str, str]] = (
        ("1", "Fleet noise", "#module1", "Anomaly rate and which rules fired most."),
        ("2", "Precursors", "#module2", "Paths and warning signs before failures."),
        ("3", "Diagnosis", "#module3", "Per-machine hypotheses and scores."),
        ("4", "Plan", "#module4", "Concrete actions and costs (when Module 4 ran)."),
        ("5", "RL policy", "#module6", "Optional simulator policy vs risk bands."),
    )
    cells = []
    for num, title, href, blurb in steps:
        cells.append(
            f'<a class="reading-step" href="{escape(href)}">'
            f'<span class="step-num">{escape(num)}</span>'
            f'<span class="step-body"><span class="step-title">{escape(title)}</span>'
            f'<span class="step-blurb">{escape(blurb)}</span></span></a>'
        )
    joined = "\n    ".join(cells)
    return f"""<aside class="start-here" aria-label="Reading guide for newcomers">
  <h3 class="start-here-title">Start here — 90 second path</h3>
  <p class="start-here-lead">Each card jumps to a section. Prefer the charts first; open tables only when you need exact rows.</p>
  <div class="reading-steps">{joined}</div>
  <p class="start-here-gloss"><strong>Terms:</strong> <abbr title="Markov decision process: toy simulator defined in mdp.json">MDP</abbr> ·
  <abbr title="First-order logic rules in the knowledge base">FOL</abbr> rules feed Module 3 ·
  Module 5 is not implemented in this repo.</p>
</aside>"""


def _render_data_status_strip(context: Mapping[str, Any]) -> str:
    def item(label: str, *, ok_load: bool, has_rows: bool, optional: bool) -> str:
        if not ok_load:
            state, msg = "miss", "File / JSON issue"
        elif has_rows:
            state, msg = "ok", "Loaded"
        else:
            state, msg = "empty", "No rows yet"
        opt = " status-optional" if optional else ""
        return (
            f'<div class="status-item{opt}">'
            f'<span class="status-dot {state}" title="{escape(msg)}"></span>'
            f'<span class="status-mod">{escape(label)}</span>'
            f'<span class="status-msg">{escape(msg)}</span></div>'
        )

    m1_ok = bool(context.get("health_core_m1"))
    m2_ok = bool(context.get("health_core_m2"))
    m3_ok = bool(context.get("health_core_m3"))
    m4_ok = bool(context.get("health_opt_m4"))
    m6_ok = bool(context.get("health_opt_m6"))
    return f"""<div class="status-strip-wrap">
  <h3 class="status-strip-title">Data availability</h3>
  <p class="status-strip-lead">Green means the artifact loaded with content; amber means loaded but empty; red means a load error (see notes below).</p>
  <div class="status-strip" role="list">
    {item("M1", ok_load=m1_ok, has_rows=int(context.get("m1_total", 0)) > 0, optional=False)}
    {item("M2", ok_load=m2_ok, has_rows=int(context.get("m2_sequence_count", 0)) + int(context.get("m2_warning_count", 0)) > 0, optional=False)}
    {item("M3", ok_load=m3_ok, has_rows=int(context.get("m3_equipment_count", 0)) > 0, optional=False)}
    {item("M4", ok_load=m4_ok, has_rows=int(context.get("m4_total_assignments", 0)) > 0, optional=True)}
    {item("M6", ok_load=m6_ok, has_rows=int(context.get("m6_policy_state_count", 0)) > 0, optional=True)}
  </div>
</div>"""


def _render_module_section_head(
    num: str,
    title: str,
    one_liner: str,
    output_files: Sequence[str],
) -> str:
    chips = "".join(
        f'<span class="out-chip" role="listitem"><code>{escape(f)}</code></span>' for f in output_files
    )
    return f"""<div class="module-head">
  <div class="module-num" aria-hidden="true">{escape(num)}</div>
  <div class="module-head-text">
    <h2>{escape(title)}</h2>
    <p class="module-one-liner">{escape(one_liner)}</p>
    <div class="file-chip-row" role="list"><span class="chip-label">Key outputs</span>{chips}</div>
  </div>
</div>"""


def _m3_equipment_top_scores(equipment: List[Mapping[str, Any]], *, limit: int = 14) -> List[tuple[str, float]]:
    rows: List[tuple[str, float]] = []
    for eq in equipment:
        eid = str(eq.get("equipment_id", "?"))
        diags = eq.get("diagnoses") or []
        if not diags:
            continue
        best = max((float(d.get("score") or 0.0) for d in diags), default=0.0)
        rows.append((eid if len(eid) <= 40 else eid[:37] + "...", best))
    rows.sort(key=lambda x: x[1], reverse=True)
    return rows[:limit]


def _render_m6_action_mix_stacked_svg(counts: Mapping[str, int]) -> str:
    """100% stacked bar for defer / inspect / repair (plus any other action ids)."""
    if not counts:
        return ""
    lc: Dict[str, int] = {}
    for k, v in counts.items():
        lc[str(k).lower()] = lc.get(str(k).lower(), 0) + int(v)
    total = sum(lc.values())
    if total <= 0:
        return ""
    order = ("defer", "inspect", "repair")
    colors = {"defer": "#2a9d8f", "inspect": "#5c6c85", "repair": "#e76f51", "_other": "#94a3b8"}
    w_bar = 420.0
    x = 0.0
    parts: List[str] = []
    for key in order:
        c = int(lc.get(key, 0))
        if c <= 0:
            continue
        frac = c / float(total)
        seg_w = max(2.0, frac * w_bar)
        parts.append(
            f'<rect x="{x:.1f}" y="6" width="{seg_w:.1f}" height="20" fill="{colors[key]}" rx="3"/>'
        )
        pct = 100.0 * c / float(total)
        if pct >= 6 and seg_w > 26:
            parts.append(
                f'<text x="{x + seg_w / 2:.1f}" y="20.5" text-anchor="middle" '
                f'font-size="10" font-weight="700" fill="#fff">{escape(key)} {pct:.0f}%</text>'
            )
        x += seg_w
    scheduled = sum(int(lc.get(k, 0)) for k in order)
    rest = total - scheduled
    if rest > 0:
        frac = rest / float(total)
        seg_w = max(2.0, frac * w_bar)
        parts.append(
            f'<rect x="{x:.1f}" y="6" width="{seg_w:.1f}" height="20" fill="{colors["_other"]}" rx="3"/>'
        )
        pct = 100.0 * rest / float(total)
        if pct >= 6 and seg_w > 26:
            parts.append(
                f'<text x="{x + seg_w / 2:.1f}" y="20.5" text-anchor="middle" '
                f'font-size="10" font-weight="700" fill="#fff">other {pct:.0f}%</text>'
            )
    inner = "\n    ".join(parts)
    return f"""<figure class="m6-mix-fig">
  <figcaption>How often each action appears in the learned policy (all states)</figcaption>
  <svg viewBox="0 0 {w_bar:.0f} 32" width="100%" style="max-height:40px" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Action mix in policy">
    {inner}
  </svg>
  <div class="m6-mix-legend"><span class="lg lg-def">defer</span><span class="lg lg-ins">inspect</span><span class="lg lg-rep">repair</span></div>
</figure>"""


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

    ec = [str(x).lower() for x in (data.get("errors_core") or [])]
    eo = [str(x).lower() for x in (data.get("errors_optional") or [])]

    def _core_bad(sub: str) -> bool:
        return any(sub in msg for msg in ec)

    def _opt_bad(sub: str) -> bool:
        return any(sub in msg for msg in eo)

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
        "health_core_m1": not _core_bad("module1"),
        "health_core_m2": not _core_bad("module2"),
        "health_core_m3": not _core_bad("module3"),
        "health_opt_m4": not _opt_bad("module4"),
        "health_opt_m6": not _opt_bad("module6"),
    }


REPORT_STYLES = """
    :root {
      --bg: #eef2f9;
      --panel: #ffffff;
      --border: #d5dde8;
      --text: #1f2937;
      --muted: #5f6b7a;
      --accent: #1e3a5f;
      --accent-soft: #e7efff;
      --ok: #2a9d8f;
      --warn: #e76f51;
      --shadow: 0 4px 14px rgba(15, 23, 42, 0.07);
      --radius: 12px;
    }
    *, *::before, *::after { box-sizing: border-box; }
    body { font-family: "Segoe UI", system-ui, -apple-system, sans-serif; margin: 0; line-height: 1.5; color: var(--text); background: var(--bg); }
    .container { max-width: 1180px; margin: 0 auto; padding: 0 24px 32px; }
    .report-hero {
      background: linear-gradient(125deg, #0f2744 0%, #1a4578 42%, #2563a8 100%);
      color: #f8fafc;
      padding: 28px 24px 32px;
      margin: 0 0 20px;
      box-shadow: 0 8px 28px rgba(15, 35, 70, 0.25);
    }
    .report-hero h1 { margin: 0 0 8px; font-size: clamp(1.35rem, 3vw, 1.85rem); font-weight: 700; letter-spacing: -0.02em; color: #fff; }
    .report-hero .hero-lead { margin: 0; font-size: 14px; opacity: 0.92; max-width: 52rem; }
    .report-hero .subtle { color: rgba(248,250,252,0.78); font-size: 12px; margin-top: 12px; }
    .report-hero .container { padding-bottom: 0; }
    h1, h2 { margin-top: 0; color: #12213f; }
    h2 { margin-bottom: 8px; font-size: 1.15rem; letter-spacing: -0.01em; }
    section {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 18px 20px;
      margin: 16px 0;
      box-shadow: var(--shadow);
    }
    nav {
      position: sticky;
      top: 0;
      z-index: 20;
      background: rgba(255,255,255,0.92);
      backdrop-filter: blur(10px);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 10px 14px;
      margin: 0 0 16px;
      display: flex;
      gap: 10px 14px;
      flex-wrap: wrap;
      align-items: center;
      box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
    }
    nav::before { content: "Jump to"; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-right: 4px; }
    nav a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      font-size: 13px;
      padding: 4px 10px;
      border-radius: 999px;
      background: #f0f4fa;
      border: 1px solid transparent;
      transition: background .15s, border-color .15s;
    }
    nav a:hover { background: var(--accent-soft); border-color: #b8cce8; }
    table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px; }
    th, td { border: 1px solid var(--border); padding: 8px 10px; text-align: left; vertical-align: top; }
    th { background: linear-gradient(180deg, #f4f7fc, #eef2f8); font-weight: 600; font-size: 12px; }
    tbody tr:nth-child(even) { background: #fafbfd; }
    .subtle { color: var(--muted); margin-top: 4px; }
    .warning { background: linear-gradient(180deg, #fffbeb, #fff8e1); padding: 12px 14px; border: 1px solid #e8d48b; border-radius: var(--radius); }
    .module-intro { color: var(--muted); margin: 0 0 14px; font-size: 14px; }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(168px, 1fr)); gap: 12px; margin: 12px 0 14px; }
    .metric-card {
      background: linear-gradient(165deg, #fbfdff 0%, #f2f7ff 100%);
      border: 1px solid #c9daf5;
      border-radius: 10px;
      padding: 12px 14px;
      min-height: 88px;
    }
    .metric-label { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #52627a; font-weight: 700; }
    .metric-value { font-size: 26px; font-weight: 800; color: #0f3d7a; margin-top: 4px; line-height: 1.1; letter-spacing: -0.02em; }
    .metric-help { font-size: 12px; color: #586983; margin-top: 8px; line-height: 1.35; }
    .metric-card--viz { grid-column: span 1; }
    .spark-wrap { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
    .spark-track { flex: 1; height: 10px; background: #e2e8f0; border-radius: 99px; overflow: hidden; }
    .spark-fill {
      display: block;
      height: 100%;
      border-radius: 99px;
      background: linear-gradient(90deg, var(--ok) 0%, #5ab3a8 35%, #e9a574 70%, var(--warn) 100%);
      min-width: 2px;
      transition: width 0.35s ease;
    }
    .spark-label { font-size: 13px; font-weight: 800; color: #0f3d7a; min-width: 3.2em; text-align: right; }
    .flow { display: none; }
    .howto { background: var(--accent-soft); border: 1px solid #c3d5ff; border-radius: 10px; padding: 10px 12px; margin-top: 8px; }
    .howto p { margin: 6px 0; }
    .blueprint-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; margin-top: 10px; }
    .blueprint-card { border: 1px solid #d4def1; border-radius: 10px; background: #fbfcff; padding: 12px; }
    .blueprint-card h3 { margin: 0 0 8px; font-size: 15px; color: #16346d; }
    .blueprint-card p { margin: 5px 0; font-size: 13px; color: #30445f; }
    .connector { margin-top: 12px; padding: 10px 12px; border-left: 4px solid #5b8def; background: linear-gradient(90deg, #f0f5ff, #fafcff); color: #2b4266; border-radius: 8px; font-size: 13px; }
    .split-overview { display: grid; grid-template-columns: 1fr; gap: 16px; margin-top: 4px; }
    @media (min-width: 900px) {
      .split-overview { grid-template-columns: 1.15fr 0.85fr; align-items: start; }
    }
    .pipeline-figure, .chart-figure { margin: 12px 0 4px; }
    .pipeline-figure figcaption, .chart-figure figcaption {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0,0,0,0);
      white-space: nowrap;
      border: 0;
    }
    .pipeline-figure svg { width: 100%; height: auto; display: block; border-radius: 10px; background: linear-gradient(180deg, #fff, #f6f9ff); border: 1px solid var(--border); }
    .chart-figure svg { display: block; border-radius: 10px; background: #fafbfd; border: 1px solid #e5eaf2; }
    details.details-panel, details.soft-panel {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0;
      margin: 12px 0;
      background: #fafbfd;
      overflow: hidden;
    }
    details.details-panel > summary, details.soft-panel > summary {
      cursor: pointer;
      font-weight: 700;
      font-size: 13px;
      padding: 10px 14px;
      color: #1a3a6e;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 8px;
      user-select: none;
    }
    details.details-panel > summary::-webkit-details-marker, details.soft-panel > summary::-webkit-details-marker { display: none; }
    details.details-panel > summary::before, details.soft-panel > summary::before {
      content: "";
      width: 7px;
      height: 7px;
      border-right: 2px solid #5f6b7a;
      border-bottom: 2px solid #5f6b7a;
      transform: rotate(-45deg);
      transition: transform 0.2s ease;
      flex-shrink: 0;
    }
    details[open].details-panel > summary::before, details[open].soft-panel > summary::before { transform: rotate(45deg); }
    details.details-panel .details-body, details.soft-panel .details-body { padding: 0 14px 14px; border-top: 1px solid #e8ecf4; }
    details.module-block { border: 1px solid #e0e7f0; border-radius: 8px; margin: 8px 0; background: #fff; }
    details.module-block > summary { cursor: pointer; padding: 10px 12px; font-weight: 600; }
    details.module-block[open] > summary { border-bottom: 1px solid #eef2f8; }
    .action-pill { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; font-weight: 700; font-family: ui-monospace, monospace; }
    .action-defer { background: #e0f2f1; color: #0d5c52; }
    .action-inspect { background: #e8ecf8; color: #334155; }
    .action-repair { background: #fde8e4; color: #9b3419; }
    .action-unknown { background: #f1f5f9; color: #475569; }
    .start-here {
      background: linear-gradient(135deg, #f0f7ff 0%, #ffffff 55%, #f5fbff 100%);
      border: 1px solid #c5daf3;
      border-radius: var(--radius);
      padding: 16px 18px 14px;
      margin: 0 0 16px;
      box-shadow: 0 2px 12px rgba(30, 58, 95, 0.06);
    }
    .start-here-title { margin: 0 0 8px; font-size: 1.05rem; color: #0f2744; }
    .start-here-lead { margin: 0 0 14px; font-size: 13px; color: #4b5c72; max-width: 58rem; line-height: 1.45; }
    .start-here-gloss { margin: 12px 0 0; font-size: 12px; color: #5f6b7a; line-height: 1.45; }
    .start-here-gloss abbr { text-decoration: underline dotted; cursor: help; }
    .reading-steps {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 10px;
    }
    .reading-step {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid #d0e3f7;
      background: #fff;
      text-decoration: none;
      color: inherit;
      transition: border-color .15s, box-shadow .15s, transform .12s;
    }
    .reading-step:hover { border-color: #7aa2f7; box-shadow: 0 4px 12px rgba(30, 74, 143, 0.1); transform: translateY(-1px); }
    .step-num {
      flex-shrink: 0;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: linear-gradient(145deg, #1a4578, #2d6bb3);
      color: #fff;
      font-weight: 800;
      font-size: 13px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .step-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .step-title { font-weight: 700; font-size: 13px; color: #12213f; }
    .step-blurb { font-size: 12px; color: #5f6b7a; line-height: 1.35; }
    .status-strip-wrap { margin: 0 0 18px; padding: 14px 16px; background: #fafcff; border: 1px solid var(--border); border-radius: var(--radius); }
    .status-strip-title { margin: 0 0 6px; font-size: 0.95rem; color: #12213f; }
    .status-strip-lead { margin: 0 0 12px; font-size: 12px; color: #5f6b7a; max-width: 52rem; }
    .status-strip { display: flex; flex-wrap: wrap; gap: 10px 12px; }
    .status-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 999px;
      font-size: 12px;
    }
    .status-item.status-optional { border-style: dashed; opacity: 0.95; }
    .status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    .status-dot.ok { background: #2a9d8f; box-shadow: 0 0 0 2px rgba(42,157,143,0.25); }
    .status-dot.empty { background: #cbd5e1; }
    .status-dot.miss { background: #e76f51; box-shadow: 0 0 0 2px rgba(231,111,81,0.22); }
    .status-mod { font-weight: 800; color: #1e3a5f; min-width: 2rem; }
    .status-msg { color: #64748b; }
    .module-head { display: flex; gap: 14px; align-items: flex-start; margin-bottom: 14px; padding-bottom: 14px; border-bottom: 1px solid #e8eef6; }
    .module-num {
      flex-shrink: 0;
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: linear-gradient(145deg, #1a4578, #3b7ec8);
      color: #fff;
      font-weight: 800;
      font-size: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 8px rgba(26, 69, 120, 0.25);
    }
    .module-head-text { min-width: 0; flex: 1; }
    .module-head-text h2 { margin-bottom: 4px; }
    .module-one-liner { margin: 0 0 10px; font-size: 13px; color: #5f6b7a; line-height: 1.45; }
    .file-chip-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
    .chip-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #7a8aa0; }
    .out-chip { padding: 3px 8px; border-radius: 6px; background: #f1f5f9; border: 1px solid #e2e8f0; font-size: 11px; }
    .out-chip code { font-size: 11px; color: #334155; }
    .stacked-fig { margin: 4px 0 14px; }
    .stacked-fig figcaption { font-size: 12px; font-weight: 700; color: #16346d; margin-bottom: 8px; }
    .stacked-bar { display: flex; height: 22px; border-radius: 8px; overflow: hidden; border: 1px solid #d8e2ec; }
    .stacked-bar .seg { min-width: 0; transition: flex-grow .3s ease; }
    .stacked-bar .seg-normal { background: linear-gradient(180deg, #5ab3a8, #2a9d8f); }
    .stacked-bar .seg-anom { background: linear-gradient(180deg, #f4a582, #e76f51); }
    .stacked-legend { display: flex; flex-wrap: wrap; gap: 16px; margin-top: 8px; font-size: 12px; color: #475569; }
    .stacked-legend .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }
    .sw-n { background: #2a9d8f; }
    .sw-a { background: #e76f51; }
    .m6-mix-fig { margin: 12px 0 8px; }
    .m6-mix-fig figcaption { font-size: 12px; font-weight: 600; color: #334155; margin-bottom: 6px; }
    .m6-mix-fig svg { border-radius: 8px; border: 1px solid #e2e8f0; background: #f8fafc; }
    .m6-mix-legend { display: flex; gap: 14px; margin-top: 6px; font-size: 11px; color: #64748b; }
    .m6-mix-legend .lg-def::before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; background: #2a9d8f; vertical-align: middle; }
    .m6-mix-legend .lg-ins::before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; background: #5c6c85; vertical-align: middle; }
    .m6-mix-legend .lg-rep::before { content: ""; display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; background: #e76f51; vertical-align: middle; }
    .err-panel { border-radius: var(--radius); overflow: hidden; border: 1px solid #e8d48b; }
    .err-panel-head { margin: 0; padding: 12px 14px; background: linear-gradient(90deg, #fff8e7, #fffdf6); font-size: 14px; color: #7a5a08; }
    .err-grid { display: grid; grid-template-columns: 1fr; gap: 0; }
    @media (min-width: 720px) { .err-grid { grid-template-columns: 1fr 1fr; } }
    .err-col { padding: 12px 14px 14px; font-size: 13px; }
    .err-col-core { background: #fffdf8; border-bottom: 1px solid #f5e5bc; }
    @media (min-width: 720px) { .err-col-core { border-bottom: none; border-right: 1px solid #f5e5bc; } }
    .err-col-opt { background: #fffef9; }
    .err-col h4 { margin: 0 0 8px; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #8a7340; }
    .err-col ul { margin: 0; padding-left: 1.1rem; }
    .err-col li { margin: 4px 0; color: #4a4a44; }
"""


def _render_module_blueprints() -> str:
    m6_blueprint_body = """
        <p><strong>Input:</strong> per-equipment risk from <code>diagnosis.json</code> (same bucketing rule as Module 4), optionally crossed with a Module 1 &ldquo;alert&rdquo; signal from <code>classifications.jsonl</code> anomaly rate or diagnosis <code>meta.m1_max_confidence</code>; plus <code>mdp.json</code> (a <em>toy</em> stochastic world: next risk level and cost after each action)</p>
        <p><strong>Processing:</strong> Q-learning runs many episodes; each episode picks a random fleet unit, starts in that unit&rsquo;s derived MDP state, and rolls the simulator for several steps</p>
        <p><strong>Output:</strong> <code>rl_policy.json</code> (greedy action per state), <code>rl_training.json</code> (per-episode return and ε schedule), <code>rl_metrics.json</code> (trained policy vs always-defer and random baselines)</p>
        <p><strong>Note:</strong> no neural nets or Module 5—tabular RL over explicit JSON dynamics. A 3-state-only MDP (risk bands only) is still supported if <code>mdp.json</code> defines only <code>risk_low</code> / <code>risk_mid</code> / <code>risk_high</code>.</p>
"""
    return f"""
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


def _render_errors_panel(context: Mapping[str, Any]) -> str:
    def _err_ul(items: List[str]) -> str:
        if not items:
            return "<li><span class=\"subtle\">None.</span></li>"
        return "\n".join(f"<li>{escape(msg)}</li>" for msg in items)

    core_errs = list(context.get("errors_core") or [])
    opt_errs = list(context.get("errors_optional") or [])
    core_block = (
        "<h4>Modules 1–3 (core)</h4>"
        "<p class=\"subtle\" style=\"margin:0 0 8px\">These files are required for a full report.</p>"
        "<ul>"
        f"{_err_ul(core_errs)}"
        "</ul>"
    )
    opt_block = (
        "<h4>Modules 4 &amp; 6 (optional)</h4>"
        "<p class=\"subtle\" style=\"margin:0 0 8px\">Missing entries here are normal if you have not run maintenance optimization or RL.</p>"
        "<ul>"
        f"{_err_ul(opt_errs)}"
        "</ul>"
    )
    return f"""<div class="warning err-panel" role="region" aria-label="Data loading notes">
  <p class="err-panel-head"><strong>Data loading notes</strong> — read this if any status dot above is red.</p>
  <div class="err-grid">
    <div class="err-col err-col-core">{core_block}</div>
    <div class="err-col err-col-opt">{opt_block}</div>
  </div>
</div>"""


def _render_module1_section(context: Mapping[str, Any]) -> str:
    rule_chart_rows = [(str(rule), float(count)) for rule, count in context["m1_top_rules"]]
    rules_chart = _render_hbar_chart("Top violated rules (count)", rule_chart_rows, as_int=True)
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
    head = _render_module_section_head(
        "1",
        "Module 1 - Rule-Based Monitoring",
        "Each sensor row is checked against threshold rules and labeled normal or anomaly.",
        ("module1/classifications.jsonl",),
    )
    mix_bar = _render_normal_anomaly_stacked(int(context["m1_total"]), int(context["m1_anomalies"]))
    return f"""
    <section id="module1">
    {head}
    <div class="metric-grid">
      <div class="metric-card"><div class="metric-label">Total readings</div><div class="metric-value">{context["m1_total"]}</div><div class="metric-help">Rows in the classifications file.</div></div>
      <div class="metric-card"><div class="metric-label">Anomalies</div><div class="metric-value">{context["m1_anomalies"]}</div><div class="metric-help">Rows where at least one rule fired.</div></div>
      <div class="metric-card"><div class="metric-label">Anomaly rate</div><div class="metric-value">{context["m1_anomaly_rate"]:.1f}%</div><div class="metric-help">Anomalies divided by total rows.</div></div>
    </div>
    {mix_bar}
    {rules_chart}
    <details>
      <summary>Top violated rules (table)</summary>
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
    <details class="soft-panel"><summary>Why this feeds downstream</summary><div class="details-body"><div class="connector"><strong>Connection:</strong> Anomaly labels and violated-rule patterns become structured facts used by Module 2 and Module 3.</div></div></details>
    </section>
"""


def _render_module2_section(context: Mapping[str, Any]) -> str:
    seq_chart_rows = [
        (" → ".join(seq.get("sequence", []))[:40], float(seq.get("frequency", 0)))
        for seq in context["m2_top_sequences"]
    ]
    seq_chart = _render_hbar_chart("Top sequences by frequency", seq_chart_rows, as_int=True)
    warn_chart_rows = [
        (str(w.get("pattern", ""))[:40], float(w.get("predictive_score", 0.0)))
        for w in context["m2_top_warning_signs"]
    ]
    warn_chart = _render_hbar_chart("Warning signs by predictive score", warn_chart_rows, as_int=False)
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
    head = _render_module_section_head(
        "2",
        "Module 2 - Failure Pattern Discovery",
        "Graph search (BFS / DFS / A*) finds event chains that tend to appear before recorded failures.",
        ("module2/sequences.json", "module2/warning_signs.json"),
    )
    return f"""
    <section id="module2">
    {head}
    {seq_chart}
    {warn_chart}
    <details class="soft-panel"><summary>Interpretation tip</summary><div class="details-body"><div class="howto">
      <p><strong>Interpretation tip:</strong> prioritize sequences with high frequency and short average time-to-failure, then validate with warning-sign predictive score and false-positive rate.</p>
    </div></div></details>
    <details>
      <summary>Top sequences (table)</summary>
      <table>
        <thead><tr><th>Sequence</th><th>Frequency</th><th>Avg time to failure</th></tr></thead>
        <tbody>{seq_rows_html}</tbody>
      </table>
    </details>
    <details>
      <summary>Warning sign ranking (table)</summary>
      <table>
        <thead><tr><th>Pattern</th><th>Predictive score</th><th>Frequency</th><th>False positive rate</th></tr></thead>
        <tbody>{warn_rows_html}</tbody>
      </table>
    </details>
    <details class="soft-panel"><summary>Why this feeds downstream</summary><div class="details-body"><div class="connector"><strong>Connection:</strong> Top warning signs and sequences are consumed by Module 3 to support or weaken diagnosis hypotheses.</div></div></details>
    </section>
"""


def _render_module3_section(context: Mapping[str, Any]) -> str:
    m3_scores = _m3_equipment_top_scores(list(context["module3_equipment"]))
    diag_strength = _render_hbar_chart(
        "Strongest hypothesis score per equipment (top entries)",
        m3_scores,
        as_int=False,
        bar_color="#6b4f9a",
    )
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
    if diagnosis_cards.strip().startswith("<p>No Module 3"):
        diag_block = diagnosis_cards
    else:
        diag_block = (
            '<details class="details-panel"><summary>Per-machine hypothesis lists (expand each asset)</summary>'
            f'<div class="details-body diag-lists">{diagnosis_cards}</div></details>'
        )
    head = _render_module_section_head(
        "3",
        "Module 3 - Diagnosis and Recommendations",
        "First-order logic style rules combine Module 1 and 2 evidence into ranked fault hypotheses per asset.",
        ("module3/diagnosis.json",),
    )
    return f"""
    <section id="module3">
      {head}
      <div class="metric-grid" style="margin-bottom:4px">
        <div class="metric-card"><div class="metric-label">Equipment blocks</div><div class="metric-value">{context["m3_equipment_count"]}</div><div class="metric-help">Each expandable block lists hypotheses for one asset.</div></div>
      </div>
      {diag_strength}
      <details class="soft-panel"><summary>Interpretation tip</summary><div class="details-body"><div class="howto">
        <p><strong>Interpretation tip:</strong> look for repeated high-score hypotheses across machines to identify fleet-wide issues vs isolated failures.</p>
      </div></div></details>
      {diag_block}
      <details class="soft-panel"><summary>Why this feeds downstream</summary><div class="details-body"><div class="connector"><strong>Connection:</strong> The highest-confidence risk signals from this section directly drive Module 4 action selection and budget tradeoffs.</div></div></details>
    </section>
"""


def _render_module4_section(context: Mapping[str, Any]) -> str:
    if not context["module4_assignments"]:
        return ""
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
    mix_rows = [(str(a), float(c)) for a, c in sorted(context["m4_action_counts"].items())]
    mix_chart = _render_hbar_chart("Selected actions (count)", mix_rows, as_int=True, bar_color="#1a6b5c")
    head = _render_module_section_head(
        "4",
        "Module 4 - Maintenance Plan (optional)",
        "Hill climbing and simulated annealing search for a good assignment of defer / inspect / repair under a budget.",
        ("module4/maintenance_plan.json",),
    )
    return f"""
<section id="module4">
  {head}
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
  {mix_chart}
  <details class="soft-panel"><summary>Action mix (text)</summary><div class="details-body"><p><strong>Action mix:</strong> {m4_action_mix or "No actions."}</p></div></details>
  <details>
    <summary>Per-equipment assignments (table)</summary>
    <table>
      <thead><tr><th>Equipment</th><th>Action</th><th>Cost</th><th>Downtime (h)</th></tr></thead>
      <tbody>{m4_rows}</tbody>
    </table>
  </details>
</section>
"""


def _render_module6_section(context: Mapping[str, Any]) -> str:
    if not context.get("m6_policy_state_count", 0):
        return ""
    m6_rich = bool(context.get("m6_rich_states"))
    m6_n = int(context.get("m6_policy_state_count", 0))
    m6_mix = " | ".join(
        f"{escape(action)}: {count}"
        for action, count in sorted(context.get("m6_action_counts", {}).items())
    )
    m6_ret = context.get("m6_mean_return_window")
    ret_block = ""
    if m6_ret is not None:
        ret_block = f"""<details class="soft-panel"><summary>Episode return and baselines (how to read the number)</summary><div class="details-body">
  <p><strong>Recent training score (mean return, last window of training episodes):</strong> {escape(str(m6_ret))}</p>
  <p class="subtle">Each episode rolls the toy MDP for several steps; per-step rewards are usually negative (costs), so episode return is negative. <strong>Less negative (closer to zero) is better,</strong> but the raw size depends only on how large rewards are in <code>mdp.json</code>—it is not a grade out of 100. Compare this mean to <code>baseline_always_defer</code> and <code>baseline_random</code> in <code>module6/rl_metrics.json</code>; beating both means the learned policy is doing well on this simulator. Full learning curve: per-episode return, ε-greedy ε, and running mean → <code>module6/rl_training.json</code>.</p>
</div></details>"""
    tn = context.get("m6_training_note")
    training_narrative = ""
    if isinstance(tn, str) and tn.strip():
        training_narrative = f"""  <details class="soft-panel" open><summary>What RL is training on</summary><div class="details-body"><div class="howto">
    <p><strong>What RL is training on:</strong> {escape(tn)}</p>
  </div></div></details>
"""
    m1a = context.get("m6_m1_alert_meta")
    m1_extra = ""
    if m6_rich and isinstance(m1a, dict):
        cp = m1a.get("classifications_path")
        ar = m1a.get("anomaly_rate_threshold")
        cf = m1a.get("confidence_fallback_threshold")
        m1_extra = f"""  <details class="soft-panel"><summary>M1-hot signal (this run)</summary><div class="details-body"><p class="subtle"><strong>M1-hot signal (this run):</strong> anomaly-rate threshold {escape(str(ar))} when classifications are available; otherwise fallback on diagnosis <code>meta.m1_max_confidence</code> ≥ {escape(str(cf))}. Classifications file: {escape(str(cp) if cp else "none (config/CLI)")}.</p></div></details>
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
            f"<td>{_action_pill_html(str(ac))}</td>"
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
    m6_counts = context.get("m6_action_counts") or {}
    m6_mix_svg = _render_m6_action_mix_stacked_svg(m6_counts) if isinstance(m6_counts, dict) else ""
    head = _render_module_section_head(
        "6",
        "Module 6 — Learned maintenance policy (reinforcement learning)",
        "Q-learning on a small MDP picks an action per simulator state; this is a teaching artifact, not live plant control.",
        ("module6/rl_policy.json", "module6/rl_metrics.json", "module6/rl_training.json"),
    )
    return f"""
<section id="module6">
  {head}
  <p class="module-intro">{intro}</p>
{training_narrative}  <details class="soft-panel"><summary>How to read the policy table</summary><div class="details-body"><div class="howto">
    {howto_read}
  </div></div></details>
{m1_extra}{ret_block}
  <p><strong>Summary of learned choices:</strong> {m6_mix or "N/A"} <span class="subtle">{summary_hint}</span></p>
  {m6_mix_svg}
  <table>
    <thead><tr><th>{state_th}</th><th>{gloss_th}</th><th>Learned action (simulator)</th></tr></thead>
    <tbody>{pol_rows}</tbody>
  </table>
  <details class="soft-panel"><summary>Compare with Module 4</summary><div class="details-body"><div class="connector"><strong>Compare with Module 4:</strong> {m4_compare}</div></div></details>
</section>
"""


def _render_overview_section(context: Mapping[str, Any], module_blueprints: str) -> str:
    m6_metric_help = (
        "MDP states with a greedy action after Q-learning (default mdp.json: six, risk × M1-hot)."
        if context.get("m6_rich_states")
        else "MDP states with a learned action (often three risk bands only)."
    )
    m6_howto = (
        "—states pair diagnosis risk with a Module 1 &ldquo;hot&rdquo; flag when using the default six-state MDP."
        if context.get("m6_rich_states")
        else "—usually one row per risk band when the MDP has only three states."
    )
    pipeline = _render_pipeline_svg()
    blueprints_block = (
        f'<details class="details-panel"><summary>Module I/O blueprints</summary>'
        f'<div class="details-body">{module_blueprints}</div></details>'
    )
    read_guide = f"""<details class="soft-panel"><summary>How to read this report</summary><div class="details-body"><div class="howto">
        <p><strong>How to read this report:</strong> Start with anomaly volume (Module 1), pattern strength (Module 2), diagnosis (Module 3), then Module 4&rsquo;s per-machine plan. <strong>Module 6 (optional)</strong> is a tabular RL demo on <code>mdp.json</code>{m6_howto} See that section for the policy table and training narrative.</p>
      </div></div></details>"""
    start_here = _render_start_here_panel()
    status_strip = _render_data_status_strip(context)
    return f"""
    <section>
      <h2>System Overview</h2>
      <p class="module-intro">Skim the five-step strip, confirm green dots, then use the dashboard cards and charts—open tables only when you need proof rows.</p>
      {start_here}
      {status_strip}
      <div class="metric-grid">
        <div class="metric-card"><div class="metric-label">Module 1 readings</div><div class="metric-value">{context["m1_total"]}</div><div class="metric-help">Rows classified as normal/anomaly.</div></div>
        <div class="metric-card metric-card--viz"><div class="metric-label">Anomaly rate (fleet)</div>{_render_anomaly_spark(float(context["m1_anomaly_rate"]))}<div class="metric-help">From Module 1 row mix.</div></div>
        <div class="metric-card"><div class="metric-label">Module 2 sequences</div><div class="metric-value">{context["m2_sequence_count"]}</div><div class="metric-help">Failure-path patterns discovered.</div></div>
        <div class="metric-card"><div class="metric-label">Module 3 equipment</div><div class="metric-value">{context["m3_equipment_count"]}</div><div class="metric-help">Machines with diagnosis blocks.</div></div>
        <div class="metric-card"><div class="metric-label">Module 4 assignments</div><div class="metric-value">{context["m4_total_assignments"]}</div><div class="metric-help">Final action decisions (if available).</div></div>
        <div class="metric-card"><div class="metric-label">Module 6 policy rows</div><div class="metric-value">{context.get("m6_policy_state_count", 0)}</div><div class="metric-help">{m6_metric_help}</div></div>
      </div>
      <div class="split-overview">
        <div>{pipeline}</div>
        <div>{read_guide}{blueprints_block}</div>
      </div>
    </section>
"""


def render_report_html(context: Dict[str, Any]) -> str:
    module_blueprints = _render_module_blueprints()
    errors_panel = _render_errors_panel(context)
    overview_section = _render_overview_section(context, module_blueprints)
    module1_section = _render_module1_section(context)
    module2_section = _render_module2_section(context)
    module3_section = _render_module3_section(context)
    module4_section = _render_module4_section(context)
    module6_section = _render_module6_section(context)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Industrial Monitoring Report</title>
  <style>
{REPORT_STYLES}
  </style>
</head>
<body>
  <header class="report-hero">
    <div class="container">
      <h1>Industrial Equipment Monitoring Report</h1>
      <p class="hero-lead">Fleet snapshot: rule-based monitoring, search-based precursors, logic-backed diagnosis, maintenance optimization, and optional tabular RL.</p>
      <p class="subtle">Source root: {escape(context["outputs_root"])}</p>
    </div>
  </header>
  <div class="container">
    {overview_section}

    <nav>
      <a href="#module1">Module 1</a>
      <a href="#module2">Module 2</a>
      <a href="#module3">Module 3</a>
      <a href="#module4">Module 4 (optional)</a>
      <a href="#module6">Module 6 — learned policy (optional)</a>
    </nav>
    {errors_panel}
    {module1_section}
    {module2_section}
    {module3_section}
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
