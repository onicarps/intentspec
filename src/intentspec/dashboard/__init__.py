"""Dashboard web UI for IntentSpec — FastAPI + Chart.js.

Local server showing coverage trends, IDS scores, stale intents.
Chart.js bundled locally (no CDN).

Usage:
    intentspec dashboard --serve [--port 8080] [--host 127.0.0.1]
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any

from intentspec.health import run_health
from intentspec.drift import run_drift


# Chart.js bundled locally — minified v4.4.0
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


def create_app(path: str = "."):
    """Create FastAPI app for the dashboard."""
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse
    except ImportError:
        raise ImportError(
            "FastAPI is required for the dashboard. "
            "Install with: pip install fastapi uvicorn"
        )

    app = FastAPI(title="IntentSpec Dashboard")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return render_dashboard(path)

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
