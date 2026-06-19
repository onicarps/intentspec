"""Tests for template validation and CrewAI adapter."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from click.testing import CliRunner

from intentspec.cli import main
from intentspec.spec.validate import validate_file

FIXTURES = Path(__file__).parent / "fixtures"
TEMPLATES = Path(__file__).parent.parent / "src" / "intentspec" / "templates"
CREWAI_FIXTURES = FIXTURES / "sample_crewai"


# --- Template validation ---------------------------------------------------

def _template_names():
    return [t.stem for t in sorted(TEMPLATES.glob("*.yaml"))]


def test_all_templates_validate():
    """All 5 built-in templates must pass schema validation."""
    for name in _template_names():
        path = TEMPLATES / f"{name}.yaml"
        intent, errors, warnings = validate_file(path)
        assert not errors, f"{name} failed validation: {errors}"


def test_five_templates_exist():
    """Exactly 5 templates must exist."""
    names = _template_names()
    expected = {"coding-agent", "research-agent", "service-agent", "data-pipeline", "multi-agent-coordinator"}
    assert set(names) == expected, f"Expected {expected}, got {set(names)}"


def test_data_pipeline_template_type():
    data = yaml.safe_load((TEMPLATES / "data-pipeline.yaml").read_text())
    assert data["agent"]["type"] == "data"


def test_multi_agent_coordinator_template_type():
    data = yaml.safe_load((TEMPLATES / "multi-agent-coordinator.yaml").read_text())
    assert data["agent"]["type"] == "coordinator"


# --- init --template CLI ---------------------------------------------------

def test_template_list():
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--template", "list"])
    assert result.exit_code == 0
    assert "coding-agent" in result.output
    assert "data-pipeline" in result.output
    assert "multi-agent-coordinator" in result.output


def test_template_unknown():
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--template", "nonexistent"])
    assert result.exit_code == 1
    assert "unknown template" in result.output


def test_template_url_placeholder():
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--template", "https://example.com/template.yaml"])
    assert result.exit_code == 1
    assert "coming soon" in result.output


def test_template_copy_data_pipeline(tmp_path):
    runner = CliRunner()
    out = tmp_path / "intent.yaml"
    result = runner.invoke(main, ["init", "--template", "data-pipeline", "-o", str(out), "--name", "my-pipeline"])
    assert result.exit_code == 0, result.output
    assert out.exists()
    data = yaml.safe_load(out.read_text())
    assert data["agent"]["type"] == "data"
    assert data["agent"]["name"] == "my-pipeline"


def test_template_copy_multi_agent(tmp_path):
    runner = CliRunner()
    out = tmp_path / "intent.yaml"
    result = runner.invoke(main, ["init", "--template", "multi-agent-coordinator", "-o", str(out), "--name", "my-coordinator"])
    assert result.exit_code == 0, result.output
    assert out.exists()
    data = yaml.safe_load(out.read_text())
    assert data["agent"]["type"] == "coordinator"
    assert data["agent"]["name"] == "my-coordinator"


def test_template_force_overwrite(tmp_path):
    runner = CliRunner()
    out = tmp_path / "intent.yaml"
    out.write_text("existing: content\n")
    result = runner.invoke(main, ["init", "--template", "coding-agent", "-o", str(out), "--force", "--name", "forced-agent"])
    assert result.exit_code == 0, result.output
    data = yaml.safe_load(out.read_text())
    assert "agent" in data


def test_template_no_force_existing(tmp_path):
    runner = CliRunner()
    out = tmp_path / "intent.yaml"
    out.write_text("existing: content\n")
    result = runner.invoke(main, ["init", "--template", "coding-agent", "-o", str(out), "--name", "test-agent"])
    assert result.exit_code == 1
    assert "already exists" in result.output


# --- CrewAI adapter -------------------------------------------------------

def test_crewai_simple():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    assert result.intent.agent_name == "researcher"
    assert len(result.intent.goals) == 2
    assert len(result.intent.tools_allowed) >= 2
    assert len(result.intent.boundaries) == 2


def test_crewai_complex():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "complex.yaml")
    assert result.intent.agent_name == "project-manager"
    assert len(result.intent.goals) == 5
    assert len(result.intent.tools_allowed) >= 4
    assert len(result.intent.boundaries) == 4


def test_crewai_minimal():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "minimal.yaml")
    assert result.intent.agent_name == "simple-agent"
    assert len(result.intent.goals) == 1
    assert len(result.intent.tools_allowed) == 0


def test_crewai_file_not_found():
    from intentspec.adapters.crewai import parse_crewai
    try:
        parse_crewai("/tmp/nonexistent_crewai_xyz.yaml")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_crewai_init_from_crewai(tmp_path):
    runner = CliRunner()
    out = tmp_path / "intent.yaml"
    result = runner.invoke(main, [
        "init", "--from", "crewai",
        str(CREWAI_FIXTURES / "simple.yaml"),
        "-o", str(out), "--yes"
    ])
    assert result.exit_code == 0, result.output
    assert out.exists()
    data = yaml.safe_load(out.read_text())
    assert data["agent"]["name"] == "researcher"


def test_crewai_format_detection():
    from intentspec.converter.format_detect import detect_format
    import os
    crewai_path = "/tmp/test_crewai_format.yaml"
    # Rename to crewai.yaml
    crewai_path = os.path.join(os.path.dirname(crewai_path), "crewai.yaml")
    with open(crewai_path, "w") as f:
        f.write("agents:\n  - role: test\n")
    try:
        assert detect_format(crewai_path) == "crewai"
    finally:
        os.unlink(crewai_path)


def test_crewai_converter_dispatch():
    from intentspec.converter import parse
    # Auto-detection requires filename "crewai.yaml", so force format
    result = parse(CREWAI_FIXTURES / "simple.yaml", format="crewai")
    assert result.intent.agent_name == "researcher"
    assert result.format == "crewai"
