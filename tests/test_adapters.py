"""Tests for framework adapters (CrewAI, etc.)."""

from __future__ import annotations

from pathlib import Path


from intentspec.spec.validate import validate_file

CREWAI_FIXTURES = Path(__file__).parent / "fixtures" / "sample_crewai"
TEMPLATES = Path(__file__).parent.parent / "src" / "intentspec" / "templates"


# --- CrewAI adapter output validation --------------------------------------

def test_crewai_simple_produces_valid_intent():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    assert result.intent.agent_name
    assert result.intent.agent_type
    assert result.intent.goals
    assert result.format == "crewai"


def test_crewai_simple_goals_content():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    goal_descriptions = [g.description for g in result.intent.goals]
    assert any("research" in g.lower() or "report" in g.lower() for g in goal_descriptions)


def test_crewai_simple_tools_extracted():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    assert "web_search" in tool_names
    assert "file_reader" in tool_names
    assert "markdown_editor" in tool_names


def test_crewai_simple_boundaries():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    assert len(result.intent.boundaries) == 2  # one per agent


def test_crewai_complex_tools_no_duplicates():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "complex.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    # github appears in both Senior Developer and Code Reviewer — should be deduplicated
    assert tool_names.count("github") == 1


def test_crewai_complex_top_level_tools():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "complex.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    # Top-level tools should also be included
    assert any("jira" in t for t in tool_names)


def test_crewai_minimal_no_agents_warning():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "minimal.yaml")
    # The minimal fixture has 1 agent, so no warning
    assert len([w for w in result.warnings if "No agents" in w]) == 0


def test_crewai_escalation_present():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    assert result.intent.escalation is not None
    assert result.intent.escalation.trigger


def test_crewai_failure_modes_present():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    assert len(result.intent.failure_modes) >= 2


def test_crewai_metadata_tags():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    assert "crewai" in result.intent.metadata.tags
    assert "imported" in result.intent.metadata.tags


def test_crewai_description_from_role_and_backstory():
    from intentspec.adapters.crewai import parse_crewai
    result = parse_crewai(CREWAI_FIXTURES / "simple.yaml")
    desc = result.intent.agent_description.lower()
    assert "researcher" in desc


def test_crewai_forced_format():
    from intentspec.converter import parse
    result = parse(CREWAI_FIXTURES / "simple.yaml", format="crewai")
    assert result.format == "crewai"


# --- Template validation via full pipeline ---------------------------------

def test_coding_agent_template_full_validate():
    intent, errors, warnings = validate_file(TEMPLATES / "coding-agent.yaml")
    assert not errors
    assert intent.agent_type == "coding"


def test_research_agent_template_full_validate():
    intent, errors, warnings = validate_file(TEMPLATES / "research-agent.yaml")
    assert not errors
    assert intent.agent_type == "research"


def test_service_agent_template_full_validate():
    intent, errors, warnings = validate_file(TEMPLATES / "service-agent.yaml")
    assert not errors
    assert intent.agent_type == "service"


def test_data_pipeline_template_full_validate():
    intent, errors, warnings = validate_file(TEMPLATES / "data-pipeline.yaml")
    assert not errors
    assert intent.agent_type == "data"
    assert len(intent.goals) >= 3
    assert len(intent.non_negotiables) >= 3
    assert len(intent.tools_allowed) >= 3


def test_multi_agent_coordinator_template_full_validate():
    intent, errors, warnings = validate_file(TEMPLATES / "multi-agent-coordinator.yaml")
    assert not errors
    assert intent.agent_type == "coordinator"
    assert len(intent.goals) >= 3
    assert len(intent.non_negotiables) >= 3
