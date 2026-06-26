"""Tests for agent spec analysis."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from intentspec.analyze_specs import analyze_directory
from intentspec.cli import main


class TestAnalyzeDirectory:
    def test_analyzes_fixtures(self):
        fixtures = Path(__file__).parent / "fixtures"
        stats = analyze_directory(str(fixtures))
        assert stats.total > 0
        assert stats.avg_ids > 0

    def test_markdown_output(self):
        fixtures = Path(__file__).parent / "fixtures"
        stats = analyze_directory(str(fixtures))
        md = stats.to_markdown()
        assert "Key Findings" in md
        assert "Sample size" in md


class TestAnalyzeCli:
    def test_analyze_command(self):
        fixtures = Path(__file__).parent / "fixtures"
        runner = CliRunner()
        result = runner.invoke(main, ["analyze", str(fixtures), "--format", "json"])
        assert result.exit_code == 0
        assert "total" in result.output