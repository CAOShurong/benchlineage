"""Generate a self-contained, auditable HTML report."""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Any

from .audit import audit_workspace
from .io import read_json
from .provenance import latest_seal
from .workspace import Workspace


def _escape(value: Any) -> str:
    return html.escape(str(value))


def _format(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "—"
        if value == 0:
            return "0"
        if abs(value) >= 10000 or abs(value) < 0.001:
            return f"{value:.{digits}g}"
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def _line_chart(points: list[dict], x_key: str, y_key: str, *, log_x: bool = False) -> str:
    usable = [
        point
        for point in points
        if isinstance(point.get(x_key), (int, float))
        and isinstance(point.get(y_key), (int, float))
        and math.isfinite(point[x_key])
        and math.isfinite(point[y_key])
        and (point[x_key] > 0 if log_x else True)
    ]
    if len(usable) < 2:
        return '<div class="empty">Not enough points for a chart.</div>'
    x_values = [math.log10(point[x_key]) if log_x else point[x_key] for point in usable]
    y_values = [point[y_key] for point in usable]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    if x_min == x_max:
        x_max += 1
    if y_min == y_max:
        y_max += 1
    width, height = 720, 250
    left, top, right, bottom = 58, 20, 20, 42

    def position_x(value: float) -> float:
        transformed = math.log10(value) if log_x else value
        return left + (transformed - x_min) / (x_max - x_min) * (width - left - right)

    def position_y(value: float) -> float:
        return top + (y_max - value) / (y_max - y_min) * (height - top - bottom)

    coordinates = " ".join(
        f"{position_x(point[x_key]):.1f},{position_y(point[y_key]):.1f}" for point in usable
    )
    circles = "".join(
        f'<circle cx="{position_x(point[x_key]):.1f}" cy="{position_y(point[y_key]):.1f}" '
        f'r="3.5"><title>{_escape(x_key)}={_format(point[x_key])}, '
        f"{_escape(y_key)}={_format(point[y_key])}</title></circle>"
        for point in usable
    )
    grid = "".join(
        f'<line x1="{left}" y1="{top + index * (height - top - bottom) / 4:.1f}" '
        f'x2="{width - right}" y2="{top + index * (height - top - bottom) / 4:.1f}"/>'
        for index in range(5)
    )
    return f"""
    <svg class="line-chart" viewBox="0 0 {width} {height}" role="img"
      aria-label="{_escape(y_key)} plotted against {_escape(x_key)}">
      <g class="grid">{grid}</g>
      <polyline points="{coordinates}"/>
      <g class="points">{circles}</g>
      <text x="{left}" y="{height - 10}">{_escape(x_key)}{" · log₁₀" if log_x else ""}</text>
      <text x="8" y="{top + 8}">{_format(y_max)}</text>
      <text x="8" y="{height - bottom + 4}">{_format(y_min)}</text>
    </svg>"""


def _analysis_card(record: dict) -> str:
    run_id = _escape(record["run_id"])
    sections = []
    for file_record in record["files"]:
        result = file_record["result"]
        kind = result["kind"]
        metrics = []
        chart = ""
        if kind == "frequency_response":
            metrics = [
                ("Cutoff", f"{_format(result['cutoff_frequency_hz'])} Hz"),
                ("Passband", f"{_format(result['passband_gain_db'])} dB"),
                ("Points", result["observations"]),
            ]
            chart = _line_chart(result["points"], "frequency_hz", "gain_db", log_x=True)
        elif kind == "power_efficiency":
            metrics = [
                ("Peak efficiency", f"{_format(result['peak_efficiency_percent'])}%"),
                ("At output", f"{_format(result['peak_output_power_w'])} W"),
                ("Mean", f"{_format(result['mean_efficiency_percent'])}%"),
            ]
            chart = _line_chart(result["points"], "output_power_w", "efficiency_percent")
        elif kind == "linear_calibration":
            metrics = [
                ("Slope", _format(result["slope"])),
                ("Intercept", _format(result["intercept"])),
                ("R²", _format(result["r_squared"], 6)),
            ]
            chart = _line_chart(result["points"], "reference", "observed")
        else:
            for name, values in list(result["columns"].items())[:3]:
                metrics.append((name, _format(values["mean"])))
        metric_html = "".join(
            f"<div><small>{_escape(label)}</small><strong>{_escape(value)}</strong></div>"
            for label, value in metrics
        )
        sections.append(
            f"""
            <section class="analysis-file">
              <div class="file-label">{_escape(file_record["path"])} · {_escape(kind)}</div>
              <div class="metric-row">{metric_html}</div>
              {chart}
            </section>"""
        )
    uncertainty = ""
    if "uncertainty_budget" in record:
        budget = record["uncertainty_budget"]
        rows = "".join(
            f"<tr><td>{_escape(item['name'])}</td><td>{_format(item['contribution'])}</td>"
            f"<td>{_format(100 * item['variance_share'], 2)}%</td><td>{_escape(item['source'])}</td></tr>"
            for item in budget["components"]
        )
        uncertainty = f"""
        <details>
          <summary>Uncertainty budget · U = {_format(budget["expanded_uncertainty"])} (k={
            _format(budget["coverage_factor"])
        })</summary>
          <table><thead><tr><th>Component</th><th>Standard contribution</th>
          <th>Variance share</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table>
        </details>"""
    return f"""
    <article class="analysis-card" data-search="{run_id.lower()}">
      <header><span>DERIVED ANALYSIS</span><h3>{run_id}</h3></header>
      {"".join(sections)}
      {uncertainty}
    </article>"""


def _instrument_rows(instruments: list[dict], calibrations: list[dict]) -> str:
    by_instrument: dict[str, list[dict]] = {}
    for calibration in calibrations:
        by_instrument.setdefault(calibration["instrument_id"], []).append(calibration)
    rows = []
    for instrument in instruments:
        candidates = sorted(
            by_instrument.get(instrument["id"], []), key=lambda item: item["due_at"], reverse=True
        )
        latest = candidates[0] if candidates else None
        calibration = (
            f'<span class="status good">valid to {_escape(latest["due_at"][:10])}</span>'
            if latest and latest["status"] == "valid"
            else '<span class="status warn">not established</span>'
        )
        rows.append(
            f"""
            <tr>
              <td><strong>{_escape(instrument["id"])}</strong><br><small>{
                _escape(instrument["kind"])
            }</small></td>
              <td>{_escape(instrument["manufacturer"])} {_escape(instrument["model"])}</td>
              <td><code>{_escape(instrument["serial"])}</code></td>
              <td>{calibration}</td>
            </tr>"""
        )
    return "".join(rows)


def build_report(
    workspace: str | Path | Workspace,
    output: str | Path,
    *,
    title: str | None = None,
    note: str = "",
) -> Path:
    bench = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    metadata = bench.require()
    instruments = bench.records("instruments")
    calibrations = bench.records("calibrations")
    studies = bench.records("studies")
    runs = bench.records("runs")
    analyses = bench.records("analysis")
    audit = audit_workspace(bench)
    seal_path = latest_seal(bench)
    seal = read_json(seal_path) if seal_path else None
    report_title = title or metadata["title"]
    analyses_html = "".join(_analysis_card(record) for record in analyses)
    studies_html = "".join(
        f"""
        <article class="study-card">
          <span>STUDY</span>
          <h3>{_escape(study["title"])}</h3>
          <p>{_escape(study["objective"])}</p>
          <div class="chips">{"".join(f"<b>{_escape(tag)}</b>" for tag in study["tags"])}</div>
        </article>"""
        for study in studies
    )
    runs_html = "".join(
        f"""
        <tr data-search="{_escape((run["id"] + " " + run["study_id"]).lower())}">
          <td><strong>{_escape(run["id"])}</strong></td>
          <td>{_escape(run["study_id"])}</td>
          <td>{_escape(run["started_at"])}</td>
          <td>{len(run["instruments"])}</td>
          <td>{len(run["raw_files"])}</td>
          <td>{len(run["deviations"])}</td>
        </tr>"""
        for run in runs
    )
    issue_rows = "".join(
        f'<li class="{kind}"><code>{_escape(item["code"])}</code> {_escape(item["message"])}</li>'
        for kind, items in (("error", audit["errors"]), ("warning", audit["warnings"]))
        for item in items
    )
    if not issue_rows:
        issue_rows = '<li class="good">No audit findings.</li>'
    evidence_digest = seal["root_digest"] if seal else "not sealed"
    payload = {
        "workspace": metadata,
        "audit": audit,
        "seal": seal,
        "studies": studies,
        "runs": runs,
        "instruments": instruments,
        "calibrations": calibrations,
        "analyses": analyses,
    }
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{_escape(report_title)} · BenchLineage</title>
<style>
:root{{--ink:#edf8f4;--muted:#92aaa5;--panel:#10231f;--panel2:#142d27;--line:#264b43;
--mint:#78e6bd;--amber:#f3bc62;--red:#ff7b83;--navy:#071411;--blue:#7fc8ff}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 85% -10%,#17483c 0,
transparent 35%),var(--navy);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,sans-serif}}
main{{width:min(1180px,calc(100% - 34px));margin:auto;padding:34px 0 80px}}
nav{{display:flex;justify-content:space-between;align-items:center;margin-bottom:70px;color:var(--muted)}}
.brand{{color:var(--ink);font-weight:800;letter-spacing:.02em}} .brand i{{font-style:normal;color:var(--mint)}}
.hero{{display:grid;grid-template-columns:1.35fr .65fr;gap:34px;align-items:end;margin-bottom:38px}}
.eyebrow,.analysis-card header span,.study-card>span{{color:var(--mint);font:700 12px/1.2 ui-monospace;
letter-spacing:.14em}} h1{{font-size:clamp(46px,7vw,82px);line-height:.96;letter-spacing:-.055em;
margin:14px 0 22px;max-width:800px}} .lede{{font-size:19px;color:#b7cdc7;max-width:720px}}
.seal-card{{background:linear-gradient(145deg,#16362e,#0e211d);border:1px solid var(--line);
border-radius:20px;padding:22px;box-shadow:0 18px 60px #0005}} .seal-card code{{display:block;
word-break:break-all;color:var(--mint);font-size:11px}} .seal-card strong{{font-size:34px}}
.kpis{{display:grid;grid-template-columns:repeat(5,1fr);border:1px solid var(--line);border-radius:18px;
overflow:hidden;margin:28px 0 72px;background:#0c1d1a}} .kpis div{{padding:22px;border-right:1px solid var(--line)}}
.kpis div:last-child{{border:0}} .kpis strong{{display:block;font-size:30px}} .kpis span{{color:var(--muted)}}
h2{{font-size:32px;letter-spacing:-.03em;margin:64px 0 10px}} .section-lede{{color:var(--muted);
max-width:760px;margin:0 0 25px}} .studies{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
.study-card,.analysis-card{{background:var(--panel);border:1px solid var(--line);border-radius:18px;
padding:23px}} .study-card h3,.analysis-card h3{{font-size:22px;margin:8px 0}} .study-card p{{color:#b3c8c2}}
.chips{{display:flex;gap:7px;flex-wrap:wrap}} .chips b{{background:#1b4037;color:#a8f0d4;border-radius:99px;
padding:4px 9px;font-size:11px}} .table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:16px}}
table{{width:100%;border-collapse:collapse;background:#0d1f1b}} th,td{{padding:13px 15px;text-align:left;
border-bottom:1px solid #1f3c35}} th{{color:var(--muted);font:700 11px ui-monospace;letter-spacing:.08em}}
tbody tr:last-child td{{border:0}} code{{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}
.status{{font-size:11px;font-weight:750;padding:4px 8px;border-radius:99px}} .status.good{{color:#9cf0ce;
background:#173b31}} .status.warn{{color:#ffd18a;background:#48381f}} .analysis-grid{{display:grid;
grid-template-columns:repeat(2,1fr);gap:18px}} .analysis-card{{padding:0;overflow:hidden}}
.analysis-card header{{padding:22px 22px 8px}} .analysis-file{{padding:0 22px 22px}} .file-label{{color:var(--muted);
font:12px ui-monospace;margin-bottom:10px}} .metric-row{{display:grid;grid-template-columns:repeat(3,1fr);
gap:8px;margin:10px 0}} .metric-row div{{background:#0a1a17;padding:11px;border-radius:10px}}
.metric-row small{{display:block;color:var(--muted)}} .metric-row strong{{font-size:18px}}
.line-chart{{width:100%;background:#091713;border-radius:12px}} .line-chart .grid line{{stroke:#1a3731}}
.line-chart polyline{{fill:none;stroke:var(--mint);stroke-width:2.2}} .line-chart circle{{fill:var(--amber)}}
.line-chart text{{fill:var(--muted);font:10px ui-monospace}} details{{border-top:1px solid var(--line);
padding:14px 22px 22px}} summary{{cursor:pointer;color:var(--blue);font-weight:700}}
.audit{{display:grid;grid-template-columns:.7fr 1.3fr;gap:18px}} .audit-score{{display:grid;place-items:center;
min-height:220px;border:1px solid var(--line);border-radius:18px;background:var(--panel)}}
.audit-score strong{{font-size:64px;color:{
        "var(--mint)" if audit["status"] == "pass" else "var(--red)"
    }}}
.findings{{margin:0;padding:18px 18px 18px 40px;background:var(--panel);border:1px solid var(--line);
border-radius:18px}} .findings li{{padding:5px}} .findings .warning{{color:#f4ca85}}
.findings .error{{color:#ff969d}} .findings .good{{color:#9de6ca}} input{{width:100%;background:#0b1b18;
color:var(--ink);border:1px solid var(--line);border-radius:12px;padding:13px;margin:5px 0 16px}}
footer{{color:var(--muted);margin-top:75px;border-top:1px solid var(--line);padding-top:25px}}
@media(max-width:850px){{.hero,.audit{{grid-template-columns:1fr}}.kpis{{grid-template-columns:1fr 1fr}}
.analysis-grid,.studies{{grid-template-columns:1fr}}}} @media print{{body{{background:white;color:#111}}
nav,input{{display:none}} .study-card,.analysis-card,.table-wrap,.audit-score,.findings{{break-inside:avoid}}}}
</style>
</head>
<body><main>
<nav><div class="brand"><i>⟟</i> BenchLineage</div><div>local evidence · deterministic audit</div></nav>
<section class="hero"><div><div class="eyebrow">ELECTRICAL-ENGINEERING EXPERIMENT RECORD</div>
<h1>{_escape(report_title)}</h1><p class="lede">{
        _escape(note or metadata.get("principles", [""])[0])
    }</p></div>
<aside class="seal-card"><span class="eyebrow">EVIDENCE ROOT</span><strong>{
        "VERIFIED" if audit["seal"] and audit["seal"]["valid"] else "OPEN"
    }</strong><code>{_escape(evidence_digest)}</code></aside></section>
<section class="kpis">
<div><strong>{len(studies)}</strong><span>studies</span></div>
<div><strong>{len(runs)}</strong><span>recorded runs</span></div>
<div><strong>{len(instruments)}</strong><span>instruments</span></div>
<div><strong>{len(analyses)}</strong><span>analyses</span></div>
<div><strong>{len(audit["errors"])}</strong><span>audit errors</span></div>
</section>
<h2>Research intent</h2><p class="section-lede">A study records why the work exists before the
measurements appear. Every run links that intent to instruments, conditions, raw files, and derived analysis.</p>
<section class="studies">{studies_html}</section>
<h2>Instrument traceability</h2><p class="section-lede">Identity and calibration are evidence, not
free-form footnotes.</p><div class="table-wrap"><table><thead><tr><th>Instrument</th><th>Identity</th>
<th>Serial</th><th>Calibration coverage</th></tr></thead><tbody>{
        _instrument_rows(instruments, calibrations)
    }</tbody></table></div>
<h2>Derived evidence</h2><p class="section-lede">Every chart below is regenerated from a referenced
raw CSV. No network service or hidden notebook state is required.</p>
<input id="analysis-search" aria-label="Filter analyses" placeholder="Filter analyses by run id…">
<section class="analysis-grid" id="analysis-grid">{analyses_html}</section>
<h2>Run ledger</h2><div class="table-wrap"><table><thead><tr><th>Run</th><th>Study</th><th>Started</th>
<th>Instruments</th><th>Raw files</th><th>Deviations</th></tr></thead><tbody>{
        runs_html
    }</tbody></table></div>
<h2>Cross-artifact audit</h2><section class="audit"><div class="audit-score"><div><span>STATUS</span>
<strong>{_escape(audit["status"].upper())}</strong></div></div><ul class="findings">{
        issue_rows
    }</ul></section>
<footer>Generated by BenchLineage 0.1.1 · self-contained HTML · no CDN · no tracker ·
raw evidence remains authoritative.</footer>
</main>
<script>
const search=document.getElementById("analysis-search");
search.addEventListener("input",()=>{{
  const query=search.value.trim().toLowerCase();
  document.querySelectorAll(".analysis-card").forEach(card=>{{
    card.hidden=query && !card.dataset.search.includes(query);
  }});
}});
window.__BENCHLINEAGE__={json.dumps(payload, ensure_ascii=False, separators=(",", ":"))};
</script></body></html>"""
    document = "\n".join(line.rstrip() for line in document.splitlines()) + "\n"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8", newline="\n")
    return output_path
