"""Regression tests for v1.3.0 independent QA report fixes."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from intentspec.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "valid_intent.yaml"


class TestPackaging:
    def test_templates_shipped_in_package(self):
        templates_dir = Path(__file__).resolve().parents[1] / "src" / "intentspec" / "templates"
        assert templates_dir.is_dir()
        names = {p.stem for p in templates_dir.glob("*.yaml")}
        assert "coding-agent" in names
        assert len(names) >= 5

    def test_mcp_gate_data_shipped(self):
        mcp_dir = Path(__file__).resolve().parents[1] / "src" / "intentspec" / "data" / "mcp"
        assert (mcp_dir / "scenarios.yaml").is_file()
        assert (mcp_dir / "aligned-filesystem.json").is_file()


class TestGateCommand:
    def test_gate_runs_without_crash(self):
        runner = CliRunner()
        result = runner.invoke(main, ["gate", str(FIXTURES)])
        assert result.exit_code in {0, 1}
        assert "Traceback" not in result.output
        assert "MCP enforcement" in result.output


class TestFormatOutput:
    def test_diff_json_is_parseable(self):
        runner = CliRunner()
        result = runner.invoke(main, ["diff", str(VALID), "--format", "json"])
        assert result.exit_code in {0, 1}
        json.loads(result.output.strip())

    def test_migrate_yaml_is_parseable(self):
        runner = CliRunner()
        result = runner.invoke(main, ["migrate", str(VALID), "--format", "yaml"])
        assert result.exit_code == 0
        yaml.safe_load(result.output)

    def test_test_json_no_test_file(self):
        runner = CliRunner()
        result = runner.invoke(main, ["test", str(VALID), "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["status"] == "no_tests"


class TestExitCodes:
    def test_drift_missing_path_exits_3(self):
        runner = CliRunner()
        result = runner.invoke(main, ["drift", "/tmp/does_not_exist_xyz.yaml"])
        assert result.exit_code == 3

    def test_validate_missing_path_exits_3(self):
        runner = CliRunner()
        result = runner.invoke(main, ["validate", "/tmp/does_not_exist_xyz.yaml"])
        assert result.exit_code == 3


class TestCoverageNoSource:
    def test_standalone_file_shows_na(self):
        runner = CliRunner()
        result = runner.invoke(main, ["coverage", str(VALID), "--format", "text"])
        assert "N/A" in result.output or "no source" in result.output.lower()