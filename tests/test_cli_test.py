"""Tests for the ``intentspec test`` CLI command.

Exercises the command via Click's :class:`CliRunner` against ``tmp_path``
fixtures, covering PATH resolution, exit-code semantics (0/1/2/3), the three
output formats, clean schema-error rendering, and the per-file performance budget.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import yaml
from click.testing import CliRunner

from intentspec.cli import main

VALID_INTENT = """\
version: "1.0"
agent:
  name: "my-agent"
  type: "coding"
  description: "A helpful coding agent for reviewing pull requests"
intent:
  goals:
    - description: "Do useful work for the team continuously"
      priority: "high"
  escalation:
    trigger: "something bad happens"
    method: "human review"
"""

PASSING_TESTS = """\
name: "passing-suite"
description: "Every case passes"
tests:
  - name: "escalation-present"
    type: "presence_check"
    field: "escalation"
  - name: "has-goals"
    type: "count_check"
    assert: "len(goals) > 0"
  - name: "agent-name-kebab"
    type: "regex_check"
    field: "agent.name"
    assert: "^[a-z][a-z0-9-]*$"
"""

ERROR_FAILING_TESTS = """\
name: "error-suite"
tests:
  - name: "has-goals"
    type: "count_check"
    assert: "len(goals) > 0"
  - name: "sub-agents-present"
    type: "presence_check"
    field: "sub_agents"
    severity: "error"
"""

WARNING_FAILING_TESTS = """\
name: "warning-suite"
tests:
  - name: "has-goals"
    type: "count_check"
    assert: "len(goals) > 0"
  - name: "sub-agents-present"
    type: "presence_check"
    field: "sub_agents"
    severity: "warning"
"""

SCHEMA_INVALID_TESTS = """\
name: "broken-suite"
tests:
  - name: "no-type-case"
    bogus_field: "oops"
"""


def _write_intent(directory: Path, *, intent: str = VALID_INTENT, test: str | None = None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    intent_path = directory / "intent.yaml"
    intent_path.write_text(intent, encoding="utf-8")
    if test is not None:
        (directory / "intent-test.yaml").write_text(test, encoding="utf-8")
    return intent_path


def test_exit_0_when_all_tests_pass(tmp_path):
    """VAL-CLI-001: every case passing yields exit 0."""
    _write_intent(tmp_path, test=PASSING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path)])
    assert result.exit_code == 0, result.output


def test_exit_1_on_error_severity_failure(tmp_path):
    """VAL-CLI-002: an error-severity failing case yields exit 1."""
    _write_intent(tmp_path, test=ERROR_FAILING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path)])
    assert result.exit_code == 1, result.output


def test_exit_2_on_warning_severity_only_failure(tmp_path):
    """VAL-CLI-003: warning-severity-only failures (no hard failures) yield exit 2."""
    _write_intent(tmp_path, test=WARNING_FAILING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path)])
    assert result.exit_code == 2, result.output


def test_exit_0_when_no_test_file(tmp_path):
    """VAL-CLI-004: valid intent.yaml with no sibling test file -> exit 0 + info message."""
    _write_intent(tmp_path)
    result = CliRunner().invoke(main, ["test", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "intent-test.yaml" in result.output
    assert "Traceback" not in result.output


def test_exit_3_when_intent_missing(tmp_path):
    """VAL-CLI-005: no resolvable intent.yaml -> exit 3 with a clear message."""
    result = CliRunner().invoke(main, ["test", str(tmp_path)])
    assert result.exit_code == 3, result.output
    assert "intent.yaml" in result.output
    assert "Traceback" not in result.output


def test_exit_3_on_schema_invalid_test_file_no_traceback(tmp_path):
    """VAL-CLI-006: schema-invalid intent-test.yaml -> exit 3, clean message, no traceback."""
    _write_intent(tmp_path, test=SCHEMA_INVALID_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path)])
    assert result.exit_code == 3, result.output
    assert "Traceback" not in result.output
    # Names the offending field/test.
    assert "bogus_field" in result.output or "type" in result.output


def test_json_format_is_parseable(tmp_path):
    """VAL-CLI-007: --format json -> json.loads-parseable with per-test name/passed + counts."""
    _write_intent(tmp_path, test=PASSING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["passed"] == 3
    assert isinstance(data["tests"], list)
    for entry in data["tests"]:
        assert "name" in entry
        assert "passed" in entry


def test_yaml_format_is_parseable(tmp_path):
    """VAL-CLI-008: --format yaml -> safe_load mapping with per-test entries."""
    _write_intent(tmp_path, test=PASSING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path), "--format", "yaml"])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(result.output)
    assert isinstance(data, dict)
    assert data["passed"] == 3
    names = {t["name"] for t in data["tests"]}
    assert {"escalation-present", "has-goals", "agent-name-kebab"} <= names


def test_text_format_lists_each_test(tmp_path):
    """VAL-CLI-009: --format text lists each executed test by name with outcome."""
    _write_intent(tmp_path, test=PASSING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path), "--format", "text"])
    assert result.exit_code == 0, result.output
    assert "escalation-present" in result.output
    assert "has-goals" in result.output
    assert "agent-name-kebab" in result.output
    assert "PASS" in result.output


def test_path_resolution_directory(tmp_path):
    """VAL-CLI-010: PATH is a directory containing intent.yaml."""
    _write_intent(tmp_path, test=PASSING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path)])
    assert result.exit_code == 0, result.output


def test_path_resolution_explicit_file(tmp_path):
    """VAL-CLI-011: PATH is an explicit intent.yaml file; uses sibling test file."""
    intent_path = _write_intent(tmp_path, test=PASSING_TESTS)
    result = CliRunner().invoke(main, ["test", str(intent_path)])
    assert result.exit_code == 0, result.output


def test_path_resolution_default_cwd(tmp_path, monkeypatch):
    """VAL-CLI-012: no PATH while CWD has intent.yaml behaves like passing that dir."""
    _write_intent(tmp_path, test=PASSING_TESTS)
    monkeypatch.chdir(tmp_path)
    explicit = CliRunner().invoke(main, ["test", str(tmp_path)])
    default = CliRunner().invoke(main, ["test"])
    assert default.exit_code == explicit.exit_code == 0, default.output


def test_all_output_via_click_captured(tmp_path):
    """VAL-CLI-013: output is emitted through click and fully captured by CliRunner."""
    _write_intent(tmp_path, test=ERROR_FAILING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path)])
    assert result.exit_code == 1
    assert result.output.strip() != ""
    assert "sub-agents-present" in result.output


def test_json_counts_consistent_with_exit_code(tmp_path):
    """VAL-CLI-014: machine-readable counts match per-test list and exit code."""
    _write_intent(tmp_path, test=ERROR_FAILING_TESTS)
    result = CliRunner().invoke(main, ["test", str(tmp_path), "--format", "json"])
    assert result.exit_code == 1, result.output
    data = json.loads(result.output)
    assert data["failed"] >= 1
    assert data["total"] == len(data["tests"])
    assert data["passed"] == sum(1 for t in data["tests"] if t["passed"])

    # warning-only path
    _write_intent(tmp_path, test=WARNING_FAILING_TESTS)
    warn = CliRunner().invoke(main, ["test", str(tmp_path), "--format", "json"])
    assert warn.exit_code == 2, warn.output
    wdata = json.loads(warn.output)
    assert wdata["failed"] == 0
    assert wdata["warnings"] >= 1


def test_performance_under_100ms(tmp_path):
    """VAL-NFR-003: a full suite run completes in under 100ms per intent file."""
    _write_intent(tmp_path, test=PASSING_TESTS)
    start = time.perf_counter()
    result = CliRunner().invoke(main, ["test", str(tmp_path), "--format", "json"])
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["total_duration_ms"] < 100.0
    assert elapsed_ms < 2000.0
