"""Dashboard web UI for IntentSpec — FastAPI + Chart.js.

Local server showing coverage trends, IDS scores, stale intents.
Chart.js loaded from CDN to keep the package small.

Usage:
    intentspec dashboard --serve [--port 8080] [--host 127.0.0.1]
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any

import tempfile

from intentspec.converter.agents_md import parse_agents_md
from intentspec.coverage import analyze_coverage
from intentspec.drift import run_drift
from intentspec.health import run_health
from intentspec.lint import lint_intent
from intentspec.report_card import grade_from_score
from intentspec.score.ids import compute_ids


# Chart.js — loaded from CDN (no local bundle to keep package small)
_CHART_JS = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"


def _scan_json(path: str = ".") -> dict[str, Any]:
    """Scan and return JSON-serializable health + drift data."""
    health = run_health(path)
    drift = run_drift(path)

    return {
        "health": health.to_dict(),
        "drift": drift.to_dict(),
    }


def render_dashboard(path: str = ".") -> str:
    """Render the full dashboard HTML page."""
    data = _scan_json(path)
    health_json = json.dumps(data["health"])
    drift_json = json.dumps(data["drift"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IntentSpec Dashboard</title>
    <script src="{_CHART_JS}"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
        h1 {{ font-size: 1.5rem; margin-bottom: 1.5rem; color: #818cf8; }}
        h2 {{ font-size: 1.1rem; margin-bottom: 0.75rem; color: #94a3b8; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
        .card {{ background: #1e293b; border-radius: 0.5rem; padding: 1rem; }}
        .metric {{ font-size: 2rem; font-weight: 700; color: #818cf8; }}
        .metric-label {{ font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }}
        .stale {{ color: #f59e0b; }}
        .error {{ color: #ef4444; }}
        .chart-container {{ position: relative; height: 200px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
        th, td {{ padding: 0.5rem; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ color: #94a3b8; font-weight: 500; }}
        .refresh {{ background: #6366f1; color: #fff; border: none; padding: 0.5rem 1rem; border-radius: 0.25rem; cursor: pointer; font-size: 0.875rem; }}
        .refresh:hover {{ background: #4f46e5; }}
        .status {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 0.5rem; }}
        .status.green {{ background: #22c55e; }}
        .status.yellow {{ background: #f59e0b; }}
        .status.red {{ background: #ef4444; }}
    </style>
</head>
<body>
    <h1>IntentSpec Dashboard</h1>
    <p style="margin-bottom: 1rem; color: #64748b;">
        Health overview for intent specs.
        <button class="refresh" onclick="location.reload()">Refresh</button>
    </p>

    <div class="grid">
        <div class="card">
            <div class="metric-label">Scanned</div>
            <div class="metric" id="metric-scanned">-</div>
        </div>
        <div class="card">
            <div class="metric-label">Valid</div>
            <div class="metric" id="metric-valid">-</div>
        </div>
        <div class="card">
            <div class="metric-label">Invalid</div>
            <div class="metric error" id="metric-invalid">-</div>
        </div>
        <div class="card">
            <div class="metric-label">Stale</div>
            <div class="metric stale" id="metric-stale">-</div>
        </div>
        <div class="card">
            <div class="metric-label">Avg IDS Score</div>
            <div class="metric" id="metric-score">-</div>
        </div>
        <div class="card">
            <div class="metric-label">Drifted</div>
            <div class="metric stale" id="metric-drifted">-</div>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>IDS Score Distribution</h2>
            <div class="chart-container">
                <canvas id="scoreChart"></canvas>
            </div>
        </div>
        <div class="card">
            <h2>Spec Status</h2>
            <div class="chart-container">
                <canvas id="statusChart"></canvas>
            </div>
        </div>
    </div>

    <div class="card" id="stale-section" style="display:none;">
        <h2>Stale Intents</h2>
        <table id="stale-table">
            <thead><tr><th>Path</th></tr></thead>
            <tbody></tbody>
        </table>
    </div>

    <div class="card" id="drift-section" style="display:none; margin-top: 1rem;">
        <h2>Drifted Specs</h2>
        <table id="drift-table">
            <thead><tr><th>Path</th><th>Days Since Commit</th><th>Reason</th></tr></thead>
            <tbody></tbody>
        </table>
    </div>

    <script>
        const health = {health_json};
        const drift = {drift_json};

        // Metrics
        document.getElementById('metric-scanned').textContent = health.scanned;
        document.getElementById('metric-valid').textContent = health.valid;
        document.getElementById('metric-invalid').textContent = health.invalid;
        document.getElementById('metric-stale').textContent = health.stale;
        document.getElementById('metric-score').textContent = health.avg_score.toFixed(1);
        document.getElementById('metric-drifted').textContent = drift.drifted;

        // Score distribution chart
        const dist = health.score_distribution;
        new Chart(document.getElementById('scoreChart'), {{
            type: 'bar',
            data: {{
                labels: Object.keys(dist),
                datasets: [{{ label: 'Specs', data: Object.values(dist),
                    backgroundColor: ['#22c55e', '#818cf8', '#f59e0b', '#ef4444'] }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true, ticks: {{ stepSize: 1 }} }} }} }}
        }});

        // Status pie chart
        new Chart(document.getElementById('statusChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Valid', 'Invalid', 'Stale'],
                datasets: [{{ data: [health.valid, health.invalid, health.stale],
                    backgroundColor: ['#22c55e', '#ef4444', '#f59e0b'] }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});

        // Stale files table
        if (health.stale_files.length > 0) {{
            document.getElementById('stale-section').style.display = 'block';
            const tbody = document.querySelector('#stale-table tbody');
            health.stale_files.forEach(f => {{
                tbody.innerHTML += `<tr><td style="font-family:monospace;font-size:0.75rem;">${{f}}</td></tr>`;
            }});
        }}

        // Drift files table
        if (drift.drifted_files.length > 0) {{
            document.getElementById('drift-section').style.display = 'block';
            const tbody = document.querySelector('#drift-table tbody');
            drift.drifted_files.forEach(d => {{
                tbody.innerHTML += `<tr>
                    <td style="font-family:monospace;font-size:0.75rem;">${{d.path}}</td>
                    <td>${{d.days_ago.toFixed(0)}}</td>
                    <td>${{d.reason}}</td>
                </tr>`;
            }});
        }}
    </script>
</body>
</html>"""


def analyze_agents_md_text(text: str) -> dict[str, Any]:
    """Analyze pasted AGENTS.md text and return a demo report card payload."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix="AGENTS.md",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(text)
        tmp_path = tmp.name

    try:
        parsed = parse_agents_md(tmp_path)
        intent = parsed.intent
        ids = compute_ids(intent)
        coverage = analyze_coverage(intent, source_text=text)
        lint = lint_intent(intent, source_text=text)

        risks: list[str] = []
        if not intent.non_negotiables:
            risks.append("No non-negotiables declared")
        if not intent.tools_denied:
            risks.append("No denied tools — no explicit blocklist")
        if coverage.overall < 0.7:
            risks.append(f"Low coverage estimate ({coverage.overall:.0%})")
        for issue in lint.errors[:3]:
            risks.append(f"{issue.rule}: {issue.message}")

        return {
            "agent_name": intent.agent_name,
            "agent_type": intent.agent_type,
            "ids_score": round(ids.score, 1),
            "grade": grade_from_score(ids.score),
            "coverage_overall": round(coverage.overall, 3),
            "lint_errors": lint.error_count,
            "lint_warnings": lint.warning_count,
            "risks": risks[:6],
            "confidence": round(parsed.average_confidence, 2),
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def render_demo_page() -> str:
    """Render the zero-install AGENTS.md paste demo."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IntentSpec — Try It Now</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #0f172a; color: #e2e8f0; padding: 2rem; max-width: 960px; margin: 0 auto; }
        h1 { color: #818cf8; margin-bottom: 0.5rem; }
        p.lead { color: #94a3b8; margin-bottom: 1.5rem; }
        textarea { width: 100%; min-height: 220px; background: #1e293b; color: #e2e8f0;
                   border: 1px solid #334155; border-radius: 0.5rem; padding: 1rem;
                   font-family: ui-monospace, monospace; font-size: 0.875rem; }
        button { margin-top: 1rem; background: #6366f1; color: #fff; border: none;
                 padding: 0.75rem 1.25rem; border-radius: 0.25rem; cursor: pointer; font-size: 1rem; }
        button:hover { background: #4f46e5; }
        #result { margin-top: 1.5rem; display: none; }
        .card { background: #1e293b; border-radius: 0.5rem; padding: 1.25rem; }
        .grade { font-size: 3rem; font-weight: 700; color: #818cf8; }
        .metric { display: inline-block; margin-right: 1.5rem; margin-top: 0.5rem; }
        .risks li { color: #f59e0b; margin: 0.25rem 0 0.25rem 1.25rem; }
        .error { color: #ef4444; margin-top: 1rem; }
        a { color: #818cf8; }
    </style>
</head>
<body>
    <h1>IntentSpec — Try It Now</h1>
    <p class="lead">Paste your AGENTS.md (or similar agent spec). Get an instant risk report — no pip install.</p>
    <textarea id="source" placeholder="# Agent Goals&#10;- Ship safely&#10;&#10;## Tools&#10;- `terminal` — run tests"></textarea>
    <button id="analyze">Analyze</button>
    <div id="result" class="card">
        <div class="grade" id="grade">-</div>
        <div>
            <span class="metric">Agent: <strong id="agent">-</strong></span>
            <span class="metric">IDS: <strong id="ids">-</strong></span>
            <span class="metric">Coverage: <strong id="coverage">-</strong></span>
        </div>
        <ul class="risks" id="risks"></ul>
        <p style="margin-top:1rem;color:#64748b;font-size:0.875rem;">
            Install for CI enforcement: <code>pip install intentspec</code> ·
            <a href="/">Dashboard</a>
        </p>
    </div>
    <p class="error" id="error" style="display:none;"></p>
    <script>
        document.getElementById('analyze').addEventListener('click', async () => {
            const text = document.getElementById('source').value.trim();
            const err = document.getElementById('error');
            const result = document.getElementById('result');
            err.style.display = 'none';
            if (!text) { err.textContent = 'Paste an agent spec first.'; err.style.display = 'block'; return; }
            const res = await fetch('/api/demo/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            const data = await res.json();
            if (!res.ok) { err.textContent = data.detail || 'Analysis failed'; err.style.display = 'block'; return; }
            document.getElementById('grade').textContent = data.grade;
            document.getElementById('agent').textContent = data.agent_name;
            document.getElementById('ids').textContent = '~' + data.ids_score + '/100';
            document.getElementById('coverage').textContent = Math.round(data.coverage_overall * 100) + '%';
            const risks = document.getElementById('risks');
            risks.innerHTML = '';
            (data.risks || []).forEach(r => { const li = document.createElement('li'); li.textContent = r; risks.appendChild(li); });
            result.style.display = 'block';
        });
    </script>
</body>
</html>"""


def create_app(path: str = "."):
    """Create FastAPI app for the dashboard."""
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse, JSONResponse
        from pydantic import BaseModel
    except ImportError:
        raise ImportError(
            "FastAPI is required for the dashboard. "
            "Install with: pip install fastapi uvicorn"
        )

    app = FastAPI(title="IntentSpec Dashboard")

    class DemoAnalyzeRequest(BaseModel):
        text: str

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return render_dashboard(path)

    @app.get("/demo", response_class=HTMLResponse)
    async def demo():
        return render_demo_page()

    @app.post("/api/demo/analyze")
    async def demo_analyze(body: DemoAnalyzeRequest):
        text = body.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        if len(text) > 200_000:
            raise HTTPException(status_code=400, detail="text too large (max 200KB)")
        try:
            return JSONResponse(analyze_agents_md_text(text))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/health")
    async def api_health():
        result = run_health(path)
        return JSONResponse(result.to_dict())

    @app.get("/api/drift")
    async def api_drift():
        result = run_drift(path)
        return JSONResponse(result.to_dict())

    return app


def serve(path: str = ".", host: str = "127.0.0.1", port: int = 8080):
    """Serve the dashboard."""
    import uvicorn

    app = create_app(path)
    uvicorn.run(app, host=host, port=port)
