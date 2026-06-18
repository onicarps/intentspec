"""Tests for converter.parse() and parse_quickstart()."""

from __future__ import annotations

import pytest

from intentspec.converter import parse, parse_quickstart
from intentspec.converter.types import ConverterError


def test_parse_missing_path_raises(tmp_path):
    with pytest.raises(ConverterError):
        parse(tmp_path / "missing.md")


def test_parse_agents_md_returns_minimal_valid_intent(tmp_path):
    fixture = tmp_path / "MyAgent.md"
    fixture.write_text("# Hello\n", encoding="utf-8")
    result = parse(fixture)
    assert result.format == "agents_md"
    assert result.intent.agent_name
    assert result.intent.agent_type == "custom"
    assert result.intent.agent_description
    assert result.intent.version == "1.0"


def test_parse_skill_md_returns_minimal_valid_intent(tmp_path):
    fixture = tmp_path / "skill.md"
    fixture.write_text("---\nname: test-skill\n---\nbody\n", encoding="utf-8")
    result = parse(fixture)
    assert result.format == "skill_md"


def test_parse_agentskills_returns_minimal_valid_intent(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "SKILL.md").write_text("---\nname: pkg\n---\n", encoding="utf-8")
    (pkg / "Scripts").mkdir()
    result = parse(pkg)
    assert result.format == "agentskills"


def test_parse_force_format_overrides_detection(tmp_path):
    fixture = tmp_path / "weird.txt"
    fixture.write_text("just some text\n", encoding="utf-8")
    result = parse(fixture, format="agents_md")
    assert result.format == "agents_md"


def test_parse_force_unknown_format_raises(tmp_path):
    fixture = tmp_path / "AGENTS.md"
    fixture.write_text("# x\n", encoding="utf-8")
    with pytest.raises(ConverterError):
        parse(fixture, format="bogus")


def test_parse_use_llm_records_warning(tmp_path):
    fixture = tmp_path / "AGENTS.md"
    fixture.write_text("# x\n", encoding="utf-8")
    result = parse(fixture, use_llm=True)
    assert any("LLM" in w for w in result.warnings)


def test_parse_quickstart_with_complete_answers():
    answers = {
        "agent_name": "My Agent",
        "agent_type": "coding",
        "agent_description": "Does coding things.",
    }
    result = parse_quickstart(answers)
    assert result.format == "quickstart"
    assert result.intent.agent_name == "my-agent"
    assert result.intent.agent_type == "coding"
    assert result.intent.agent_description == "Does coding things."
    assert result.confidences["agent.name"] == 1.0
    assert result.sources["agent.name"].extractor == "user"


def test_parse_quickstart_falls_back_for_invalid_type():
    answers = {
        "agent_name": "agent",
        "agent_type": "bogus",
        "agent_description": "x",
    }
    result = parse_quickstart(answers)
    assert result.intent.agent_type == "custom"


def test_parse_quickstart_truncates_long_description():
    answers = {
        "agent_name": "agent",
        "agent_type": "coding",
        "agent_description": "x" * 500,
    }
    result = parse_quickstart(answers)
    assert len(result.intent.agent_description) == 200


def test_parse_quickstart_handles_empty_answers():
    result = parse_quickstart({})
    assert result.intent.agent_name
    assert result.intent.agent_type == "custom"
    assert result.intent.agent_description


def test_parse_does_not_mutate_filesystem(tmp_path):
    fixture = tmp_path / "AGENTS.md"
    fixture.write_text("# x\n", encoding="utf-8")
    before = sorted(p.name for p in tmp_path.iterdir())
    parse(fixture)
    after = sorted(p.name for p in tmp_path.iterdir())
    assert before == after
