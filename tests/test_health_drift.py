"""Tests for health and drift commands."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from intentspec.cli import main
from intentspec.drift import run_drift, DriftResult
from intentspec.health import run_health, HealthResult


# --- Health Module ---

class TestHealthResult:
    """Test HealthResult data class."""

    def test_score_distribution(self):
        result = HealthResult()
        result.scores = [95, 85, 75, 45, 92, 68]
        dist = result.score_distribution
        assert dist["90-100"] == 2
        assert dist["70-89"] == 2
        assert dist["50-69"] == 1
        assert dist["0-49"] == 1

    def test_to_dict(self):
        result = HealthResult(scanned=5, valid=3, invalid=2, stale=1, avg_score=75.5)
        d = result.to_dict()
        assert d["scanned"] == 5
        assert d["valid"] == 3
        assert d["avg_score"] == 75.5
        assert "score_distribution" in d

    def test_to_text(self):
        result = HealthResult(scanned=3, valid=3, avg_score=80.0)
        text = result.to_text()
        assert "IntentSpec Health Report" in text
        assert "Scanned:    3" in text
        assert "Avg Score:  80.0" in text


class TestRunHealth:
    """Test run_health function."""

    def test_health_with_valid_files(self, tmp_path):
        spec = tmp_path / "intent.yaml"
        spec.write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test agent\nintent: {}\n"
        )
        result = run_health(str(tmp_path))
        assert result.scanned == 1
        assert result.valid == 1
        assert result.avg_score > 0
        assert result.orphaned == 1

    def test_health_not_orphaned_with_agents_md(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test agent\nintent: {}\n"
        )
        result = run_health(str(tmp_path))
        assert result.orphaned == 0

    def test_health_with_invalid_file(self, tmp_path):
        (tmp_path / "intent.yaml").write_text("invalid: yaml: [")
        result = run_health(str(tmp_path))
        assert result.scanned == 1
        assert result.invalid >= 1

    def test_health_empty_directory(self, tmp_path):
        result = run_health(str(tmp_path))
        assert result.scanned == 0

    def test_health_nonexistent_path(self):
        result = run_health("/nonexistent/path")
        assert result.scanned == 0
        assert len(result.errors) > 0

    def test_health_stale_detection(self, tmp_path):
        spec = tmp_path / "intent.yaml"
        spec.write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test\nintent: {}\n"
        )
        # Set mtime to 60 days ago
        import time
        old_time = time.time() - (60 * 86400)
        os.utime(str(spec), (old_time, old_time))

        result = run_health(str(tmp_path), stale_days=30)
        assert result.scanned == 1
        assert result.stale >= 1
        assert len(result.stale_files) >= 1


class TestCLIHealth:
    """Test health CLI command."""

    def test_health_text(self, tmp_path):
        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test agent\nintent: {}\n"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["health", str(tmp_path)])
        assert result.exit_code == 2  # orphaned spec warning
        assert "Health Report" in result.output

    def test_health_exit_code_invalid(self, tmp_path):
        (tmp_path / "intent.yaml").write_text("invalid: yaml: [")
        runner = CliRunner()
        result = runner.invoke(main, ["health", str(tmp_path)])
        assert result.exit_code == 1

    def test_health_json(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test agent\nintent: {}\n"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["health", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "scanned" in data

    def test_health_yaml(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# Agent\n", encoding="utf-8")
        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test agent\nintent: {}\n"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["health", str(tmp_path), "--format", "yaml"])
        assert result.exit_code == 0
        data = yaml.safe_load(result.output)
        assert "scanned" in data


# --- Drift Module ---

class TestDriftResult:
    """Test DriftResult data class."""

    def test_to_dict(self):
        result = DriftResult(scanned=5, drifted=2)
        d = result.to_dict()
        assert d["scanned"] == 5
        assert d["drifted"] == 2

    def test_to_text(self):
        result = DriftResult(scanned=5, drifted=1)
        result.drifted_files = [{"path": "test/intent.yaml", "days_ago": 45, "reason": "stale"}]
        text = result.to_text()
        assert "Drift Report" in text
        assert "Drifted:  1" in text


class TestRunDrift:
    """Test run_drift function."""

    def test_drift_no_files(self, tmp_path):
        result = run_drift(str(tmp_path))
        assert result.scanned == 0
        assert result.drifted == 0

    def test_drift_with_file(self, tmp_path):
        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test\nintent: {}\n"
        )
        result = run_drift(str(tmp_path))
        assert result.scanned == 1

    def test_drift_nonexistent_path(self):
        result = run_drift("/nonexistent/path")
        assert result.scanned == 0
        assert len(result.errors) > 0


class TestCLIDrift:
    """Test drift CLI command."""

    def test_drift_text(self, tmp_path):
        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test\nintent: {}\n"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["drift", str(tmp_path)])
        assert result.exit_code in (0, 1)
        assert "Drift" in result.output

    def test_drift_json(self, tmp_path):
        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test\nintent: {}\n"
        )
        runner = CliRunner()
        result = runner.invoke(main, ["drift", str(tmp_path), "--format", "json"])
        assert result.exit_code in (0, 1)
        data = json.loads(result.output)
        assert "scanned" in data

    def test_drift_custom_threshold(self, tmp_path):
        (tmp_path / "intent.yaml").write_text(
            "version: '1.0'\nagent:\n  name: test\n  type: custom\n  description: test\nintent: {}\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            main, ["drift", str(tmp_path), "--threshold-days", "7"]
        )
        assert result.exit_code in (0, 1)
