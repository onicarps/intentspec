"""Tests for dashboard module and CLI command."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from intentspec.cli import main


class TestDashboardRender:
    """Test dashboard HTML rendering."""

    def test_render_dashboard(self):
        from intentspec.dashboard import render_dashboard

        html = render_dashboard(".")
        assert "<title>IntentSpec Dashboard</title>" in html
        assert "Chart.js" in html or "chart" in html.lower()
        assert "IDS Score Distribution" in html

    def test_render_dashboard_with_data(self, tmp_path):
        from intentspec.dashboard import render_dashboard

        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test agent\nintent: {}\n"
        )
        html = render_dashboard(str(tmp_path))
        assert "metric-scanned" in html
        assert "metric-valid" in html


class TestDashboardApp:
    """Test FastAPI app creation."""

    def test_create_app_without_fastapi(self):
        with patch.dict("sys.modules", {"fastapi": None}):
            with pytest.raises(ImportError, match="FastAPI is required"):
                from intentspec.dashboard import create_app

                create_app(".")

    def test_create_app_with_fastapi(self):
        pytest.importorskip("fastapi")
        from intentspec.dashboard import create_app

        app = create_app(".")
        assert app is not None


class TestDashboardCLI:
    """Test dashboard CLI command."""

    def test_dashboard_without_fastapi(self):
        runner = CliRunner()
        with patch("intentspec.cli._HAS_DASHBOARD", False):
            result = runner.invoke(main, ["dashboard"])
        assert result.exit_code == 1
        assert "FastAPI" in result.output

    def test_dashboard_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["dashboard", "--help"])
        assert result.exit_code == 0
        assert "FastAPI" in result.output or "dashboard" in result.output.lower()
