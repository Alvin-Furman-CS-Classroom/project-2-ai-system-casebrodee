"""Static HTML reporting for module outputs."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Dict, List


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


def load_module_outputs(outputs_root: Path) -> Dict[str, Any]:
    module1_rows, m1_err = _read_jsonl(outputs_root / "module1" / "classifications.jsonl")
    module2_sequences, m2_seq_err = _read_json(outputs_root / "module2" / "sequences.json")
    module2_warnings, m2_warn_err = _read_json(outputs_root / "module2" / "warning_signs.json")
    module3_diag, m3_err = _read_json(outputs_root / "module3" / "diagnosis.json")
    module4_plan, m4_err = _read_json(outputs_root / "module4" / "maintenance_plan.json")

    return {
        "module1_rows": module1_rows or [],
        "module2_sequences": (module2_sequences or {}).get("sequences", []),
        "module2_warning_signs": (module2_warnings or {}).get("warning_signs", []),
        "module3_equipment": (module3_diag or {}).get("equipment", []),
        "module4_assignments": (module4_plan or {}).get("assignments", []),
        "module4_totals": (module4_plan or {}).get("totals", {}),
        "errors": [e for e in [m1_err, m2_seq_err, m2_warn_err, m3_err, m4_err] if e],
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

    return {
        **data,
        "m1_total": len(m1_rows),
        "m1_anomalies": len(anomalies),
        "m1_anomaly_rate": (len(anomalies) / len(m1_rows) * 100.0) if m1_rows else 0.0,
        "m1_top_rules": top_rules,
        "m2_top_sequences": top_sequences,
        "m2_top_warning_signs": top_warning_signs,
    }


def render_report_html(context: Dict[str, Any]) -> str:
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
        module4_section = f"""
<section id="module4">
  <h2>Module 4 - Maintenance Plan (optional)</h2>
  <p>Objective: {escape(str(totals.get('objective', 0.0)))} | Maintenance cost: {escape(str(totals.get('maintenance_cost', 0.0)))} | Failure penalty: {escape(str(totals.get('failure_penalty', 0.0)))}</p>
  <table>
    <thead><tr><th>Equipment</th><th>Action</th><th>Cost</th><th>Downtime (h)</th></tr></thead>
    <tbody>{m4_rows}</tbody>
  </table>
</section>
"""

    errors_html = "\n".join(
        f"<li>{escape(msg)}</li>" for msg in context["errors"]
    ) or "<li>No data loading warnings.</li>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Industrial Monitoring Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; line-height: 1.4; }}
    h1, h2 {{ margin-top: 24px; }}
    nav a {{ margin-right: 12px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f5f5f5; }}
    .subtle {{ color: #555; }}
    .warning {{ background: #fff8e1; padding: 8px; border: 1px solid #f0d98c; }}
  </style>
</head>
<body>
  <h1>Industrial Equipment Monitoring Report</h1>
  <p class="subtle">Source root: {escape(context["outputs_root"])}</p>
  <nav>
    <a href="#module1">Module 1</a>
    <a href="#module2">Module 2</a>
    <a href="#module3">Module 3</a>
    <a href="#module4">Module 4 (optional)</a>
  </nav>
  <div class="warning"><strong>Data loading notes:</strong><ul>{errors_html}</ul></div>

  <section id="module1">
    <h2>Module 1 - Rule-Based Monitoring</h2>
    <p>Total readings: {context["m1_total"]} | Anomalies: {context["m1_anomalies"]} ({context["m1_anomaly_rate"]:.1f}%)</p>
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
  </section>

  <section id="module2">
    <h2>Module 2 - Failure Pattern Discovery</h2>
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
  </section>

  <section id="module3">
    <h2>Module 3 - Diagnosis and Recommendations</h2>
    {diagnosis_cards}
  </section>
  {module4_section}
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
