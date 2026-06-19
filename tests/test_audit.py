"""Tests for `intentspec audit-report` and audit.generate_audit."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml
from click.testing import CliRunner

from intentspec.audit import generate_audit
from intentspec.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "valid_intent.yaml"
INVALID = FIXTURES / "invalid_intent.yaml"

_MINIMAL = """version: "1.0"
agent:
  name: "minimal-agent"
  type: "custom"
  description: "A minimal valid agent used for audit-report edge testing."
intent: {}
"""


def _write_minimal(tmp_path: Path) -> Path:
    p = tmp_path / "minimal_intent.yaml"
    p.write_text(_MINIMAL, encoding="utf-8")
    return p


# --- generate_audit: text rendering ---------------------------------------

def test_text_report_has_header():
    out = generate_audit(VALID, output_format="text")
    assert "IntentSpec Compliance Report" in out
    assert re.search(r"^#+\s+IntentSpec Compliance Report", out, re.MULTILINE)


def test_text_agent_inventory_identity_fields():
    out = generate_audit(VALID, output_format="text")
    assert "code-reviewer" in out
    assert "coding" in out
    assert "Reviews PRs for code quality" in out
    assert "1.0" in out


def test_text_full_spec_dump_every_section():
    out = generate_audit(VALID, output_format="text")
    assert "Identify bugs, security vulnerabilities" in out
    assert "Always check for OWASP Top 10" in out
    assert "Never approve code with hardcoded secrets" in out
    assert "github_api" in out
    assert "production_deployer" in out
    assert "PR review in github.com/acme/backend repo" in out
    assert "CVSS >= 7.0" in out
    assert "Agent approves code with subtle logic bugs" in out


def test_text_allowed_and_denied_labels_present():
    out = generate_audit(VALID, output_format="text").lower()
    assert "allowed" in out
    assert "denied" in out


def test_text_ids_score_and_breakdown():
    out = generate_audit(VALID, output_format="text")
    assert re.search(r"~\d+", out)
    for comp in (
        "tool_coverage",
        "goal_coverage",
        "constraint_cov",
        "non_negot_cov",
        "freshness",
        "completeness",
        "consistency",
    ):
        assert comp in out, f"missing breakdown component {comp}"


def test_text_soc2_and_eu_ai_act_preamble():
    out = generate_audit(VALID, output_format="text")
    assert "SOC 2" in out
    assert "EU AI Act" in out


def test_text_version_history_section():
    out = generate_audit(VALID, output_format="text")
    assert "Version History" in out


def test_text_footer_timestamp_and_hash():
    out = generate_audit(VALID, output_format="text")
    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", out)
    assert re.search(r"[0-9a-f]{64}", out)


def test_text_metadata_rendered():
    out = generate_audit(VALID, output_format="text")
    assert "backend-team@acme.com" in out
    assert "active" in out
    assert "monthly" in out


# --- hash correctness ------------------------------------------------------

def test_hash_matches_independent_sha256():
    out = generate_audit(VALID, output_format="json")
    data = json.loads(out)
    expected = hashlib.sha256(VALID.read_bytes()).hexdigest()
    assert data["sha256"] == expected


def test_hash_changes_on_content_change(tmp_path):
    a = tmp_path / "a.yaml"
    a.write_bytes(VALID.read_bytes())
    first = json.loads(generate_audit(a, output_format="json"))["sha256"]
    with open(a, "ab") as fh:
        fh.write(b"\n# extra comment\n")
    second = json.loads(generate_audit(a, output_format="json"))["sha256"]
    assert first != second


# --- json / yaml -----------------------------------------------------------

def test_json_valid_and_required_keys():
    data = json.loads(generate_audit(VALID, output_format="json"))
    assert data["agent"]["name"] == "code-reviewer"
    assert data["agent"]["type"] == "coding"
    assert data["agent"]["description"]
    assert data["agent"]["version"] == "1.0"
    assert "intent" in data
    assert data["intent"]["goals"]
    assert data["intent"]["tools"]["allowed"]
    assert data["intent"]["tools"]["denied"]
    assert "score" in data and "breakdown" in data["score"]
    assert re.fullmatch(r"[0-9a-f]{64}", data["sha256"])
    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", data["generated_at"])


def test_yaml_valid_and_same_data():
    data = yaml.safe_load(generate_audit(VALID, output_format="yaml"))
    assert data["agent"]["name"] == "code-reviewer"
    assert data["score"]["breakdown"]
    assert re.fullmatch(r"[0-9a-f]{64}", data["sha256"])
    assert data["intent"]["tools"]["denied"]


def test_ids_matches_score_command():
    runner = CliRunner()
    score_res = runner.invoke(main, ["score", str(VALID), "--format", "json"])
    assert score_res.exit_code == 0, score_res.output
    score_val = json.loads(score_res.output)["score"]
    audit = json.loads(generate_audit(VALID, output_format="json"))
    assert audit["score"]["ids"] == score_val


# --- CLI wiring & exit codes ----------------------------------------------

def test_cli_valid_exits_0_with_header():
    runner = CliRunner()
    res = runner.invoke(main, ["audit-report", str(VALID)])
    assert res.exit_code == 0, res.output
    assert "IntentSpec Compliance Report" in res.output


def test_cli_json_format_parses():
    runner = CliRunner()
    res = runner.invoke(main, ["audit-report", str(VALID), "--format", "json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["agent"]["name"] == "code-reviewer"


def test_cli_yaml_format_parses():
    runner = CliRunner()
    res = runner.invoke(main, ["audit-report", str(VALID), "--format", "yaml"])
    assert res.exit_code == 0, res.output
    data = yaml.safe_load(res.output)
    assert data["agent"]["name"] == "code-reviewer"


def test_cli_missing_file_exits_3():
    runner = CliRunner()
    res = runner.invoke(main, ["audit-report", "/tmp/does_not_exist_intent_xyz.yaml"])
    assert res.exit_code == 3
    assert res.output.strip()


def test_cli_schema_invalid_exits_1():
    runner = CliRunner()
    res = runner.invoke(main, ["audit-report", str(INVALID)])
    assert res.exit_code == 1
    assert res.output.strip()


def test_cli_directory_resolution(tmp_path):
    d = tmp_path / "auditdir"
    d.mkdir()
    (d / "intent.yaml").write_bytes(VALID.read_bytes())
    runner = CliRunner()
    res = runner.invoke(main, ["audit-report", str(d)])
    assert res.exit_code == 0, res.output
    assert "IntentSpec Compliance Report" in res.output


def test_cli_minimal_intent_all_formats(tmp_path):
    p = _write_minimal(tmp_path)
    runner = CliRunner()
    for fmt in ("text", "json", "yaml"):
        res = runner.invoke(main, ["audit-report", str(p), "--format", fmt])
        assert res.exit_code == 0, f"{fmt}: {res.output}"
        assert "Traceback" not in res.output


def test_minimal_intent_generate_audit_all_formats(tmp_path):
    p = _write_minimal(tmp_path)
    for fmt in ("text", "json", "yaml"):
        out = generate_audit(p, output_format=fmt)
        assert out
