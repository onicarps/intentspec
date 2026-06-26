"""Tests for shareable agent report card."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from intentspec.cli import main
from intentspec.report_card import ReportCardResult, generate_report_card


_VALID_SPEC = """\
version: '1.0'
agent:
  name: demo-agent
  type: coding
  description: Demo agent for report card tests
intent:
  goals:
    - description: Ship features safely
  tools:
    allowed:
      - name: terminal
        rationale: Run build and test commands
    denied:
      - name: network
        rationale: Prevent exfiltration
  non_negotiables:
    - rule: Never commit secrets
      severity: hard
  constraints:
    - rule: Never modify production data
      enforceable: true
metadata:
  status: active
"""


class TestReportCardResult:
    def test_to_markdown_contains_grade(self):
        result = ReportCardResult(
            agent_name="demo",
            agent_type="coding",
            ids_score=82.5,
            grade="B",
            coverage_overall=0.85,
            lint_errors=0,
            lint_warnings=1,
            risks=["No denied tools"],
            highlights=["2 allowed tool(s) with rationale"],
        )
        md = result.to_markdown()
        assert "Grade:** B" in md
        assert "demo" in md
        assert "Risks" in md

    def test_to_text_box(self):
        result = ReportCardResult(
            agent_name="x",
            agent_type="custom",
            ids_score=90,
            grade="A",
            coverage_overall=1.0,
            lint_errors=0,
            lint_warnings=0,
        )
        assert "AGENT REPORT CARD" in result.to_text()


class TestGenerateReportCard:
    def test_valid_spec(self, tmp_path: Path):
        spec = tmp_path / "intent.yaml"
        spec.write_text(_VALID_SPEC)
        result = generate_report_card(spec)
        assert result.agent_name == "demo-agent"
        assert result.grade in {"A", "B", "C", "D", "F"}
        assert result.lint_errors >= 0


class TestReportCli:
    def test_report_json(self, tmp_path: Path):
        spec = tmp_path / "intent.yaml"
        spec.write_text(_VALID_SPEC)
        runner = CliRunner()
        result = runner.invoke(main, ["report", str(spec), "--format", "json"])
        assert result.exit_code in {0, 2}
        payload = json.loads(result.output)
        assert payload["agent_name"] == "demo-agent"

    def test_report_markdown_output_file(self, tmp_path: Path):
        spec = tmp_path / "intent.yaml"
        spec.write_text(_VALID_SPEC)
        out = tmp_path / "card.md"
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["report", str(spec), "--format", "markdown", "-o", str(out)],
        )
        assert result.exit_code in {0, 2}
        assert out.exists()
        assert "Agent Report Card" in out.read_text()