"""Tests for intentspec status command."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from intentspec.cli import main
from intentspec.status import run_status

VALID_INTENT = """\
version: "1.0"
agent:
  name: "status-agent"
  type: "coding"
  description: "A helpful coding agent for status command tests"
intent:
  goals:
    - description: "Provide reliable CI status output for GitHub Actions"
      priority: "high"
      success_criteria: "status JSON includes validate, lint, and test checks"
  escalation:
    trigger: "check failure"
    method: "human review"
  failure_modes:
    - mode: "missing spec"
      mitigation: "run intentspec init"
  boundaries:
    - scope: "CI validation"
      out_of_scope: "runtime monitoring"
  tools:
    denied:
      - name: "rm_rf"
        rationale: "Prevent destructive operations"
"""


class TestRunStatus:
    def test_valid_intent_passes_or_warns(self, tmp_path: Path) -> None:
        intent = tmp_path / "intent.yaml"
        intent.write_text(VALID_INTENT, encoding="utf-8")
        result = run_status([str(tmp_path)])
        assert result.exit_code in (0, 2)
        assert "validate" in result.checks
        assert "lint" in result.checks
        assert "test" in result.checks

    def test_missing_intent_is_fatal(self, tmp_path: Path) -> None:
        result = run_status([str(tmp_path / "missing.yaml")])
        assert result.exit_code == 3

    def test_json_shape(self, tmp_path: Path) -> None:
        intent = tmp_path / "intent.yaml"
        intent.write_text(VALID_INTENT, encoding="utf-8")
        payload = run_status([str(tmp_path)]).to_dict()
        assert "passed" in payload
        assert "issues" in payload
        assert "checks" in payload
        assert set(payload["checks"]) == {"validate", "lint", "test"}


class TestStatusCLI:
    def test_status_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0

    def test_status_json_output(self, tmp_path: Path) -> None:
        intent = tmp_path / "intent.yaml"
        intent.write_text(VALID_INTENT, encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["status", str(tmp_path), "--format", "json"])
        assert result.exit_code in (0, 1, 2)
        data = json.loads(result.output)
        assert "checks" in data

    def test_status_yaml_output(self, tmp_path: Path) -> None:
        intent = tmp_path / "intent.yaml"
        intent.write_text(VALID_INTENT, encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(main, ["status", str(tmp_path), "--format", "yaml"])
        assert result.exit_code in (0, 1, 2)
        data = yaml.safe_load(result.output)
        assert "checks" in data