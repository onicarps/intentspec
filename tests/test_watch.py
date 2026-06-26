"""Tests for watch mode and pre-commit installation."""

from __future__ import annotations

import time
from pathlib import Path

import yaml
from click.testing import CliRunner

from intentspec.cli import main
from intentspec.precommit import install_pre_commit
from intentspec.watch import run_watch_cycle, watch_exit_code

VALID_INTENT = """\
version: "1.0"
agent:
  name: "watch-agent"
  type: "coding"
  description: "A helpful coding agent for watch mode tests"
intent:
  goals:
    - description: "Run structural checks quickly on every save"
      priority: "high"
      success_criteria: "validate and lint complete under 100ms"
  escalation:
    trigger: "validation failure"
    method: "human review"
  failure_modes:
    - mode: "stale spec"
      mitigation: "re-run intentspec watch"
  boundaries:
    - scope: "local development"
      out_of_scope: "production deploys"
  tools:
    denied:
      - name: "rm_rf"
        rationale: "Prevent destructive operations"
"""


def _write_valid_intent(tmp_path: Path) -> Path:
    intent = tmp_path / "intent.yaml"
    intent.write_text(VALID_INTENT, encoding="utf-8")
    return intent


class TestRunWatchCycle:
    def test_valid_intent_passes(self, tmp_path: Path) -> None:
        intent = _write_valid_intent(tmp_path)
        result = run_watch_cycle(intent)
        assert result.valid is True
        assert watch_exit_code(result) == 0

    def test_schema_error_fails(self, tmp_path: Path) -> None:
        intent = tmp_path / "intent.yaml"
        intent.write_text("version: [broken\n", encoding="utf-8")
        result = run_watch_cycle(intent)
        assert result.valid is False
        assert watch_exit_code(result) == 1


class TestWatchDirectory:
    def test_rerun_after_modify(self, tmp_path: Path) -> None:
        intent = _write_valid_intent(tmp_path)
        first = run_watch_cycle(intent)
        assert first.valid is True

        intent.write_text(VALID_INTENT + "\n# touched\n", encoding="utf-8")
        time.sleep(0.01)
        second = run_watch_cycle(intent)
        assert second.valid is True


class TestPreCommitInstall:
    def test_install_creates_config(self, tmp_path: Path) -> None:
        path = install_pre_commit(tmp_path)
        assert path.exists()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "repos" in data

    def test_init_pre_commit_flag(self, tmp_path: Path) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--pre-commit"])
            assert result.exit_code == 0
            assert Path(".pre-commit-config.yaml").exists()


class TestWatchCLI:
    def test_watch_once_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["watch", "--help"])
        assert result.exit_code == 0
        assert "--once" in result.output

    def test_watch_once_runs(self, tmp_path: Path) -> None:
        _write_valid_intent(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["watch", str(tmp_path), "--once"])
        assert result.exit_code in (0, 2)
        assert "intent.yaml" in result.output.lower() or "PASS" in result.output