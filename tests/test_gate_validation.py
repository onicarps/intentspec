"""Tests for ONI-195 gate validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from intentspec.cli import main
from intentspec.gate_validation import (
    check_converter_accuracy,
    check_mcp_fp_rate,
    run_gate_validation,
)


class TestMCPGate:
    def test_mcp_fp_rate_passes(self):
        check = check_mcp_fp_rate()
        assert check.status == "pass"
        assert "0.0%" in check.measured or "0%" in check.measured


class TestConverterGate:
    def test_converter_meets_threshold(self):
        check = check_converter_accuracy()
        assert check.status == "pass"


class TestRunGateValidation:
    def test_automatable_checks_mostly_pass(self):
        report = run_gate_validation(str(Path(__file__).parent))
        automatable = [c for c in report.checks if c.status in {"pass", "fail"}]
        passed = sum(1 for c in automatable if c.status == "pass")
        assert passed >= 4, report.to_markdown()

    def test_report_markdown(self):
        report = run_gate_validation(str(Path(__file__).parent))
        md = report.to_markdown()
        assert "ONI-195" in md
        assert "MCP enforcement" in md


class TestGateCli:
    def test_gate_command_json(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["gate", str(Path(__file__).parent), "--format", "json"],
        )
        assert result.exit_code in {0, 1}
        assert "checks" in result.output