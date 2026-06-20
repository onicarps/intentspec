"""Tests for the OpenAI Agents SDK adapter."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from intentspec.converter.format_detect import detect_format
from intentspec.converter.types import ConverterError

OA_FIXTURES = Path(__file__).parent / "fixtures" / "sample_openai_agents"


# --- OpenAI Agents adapter: simple fixture ----------------------------------

def test_openai_agents_simple_produces_valid_intent():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    assert result.intent.agent_name
    assert result.intent.agent_type == "custom"
    assert result.intent.goals
    assert result.format == "openai_agents"


def test_openai_agents_simple_agent_name():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    assert result.intent.agent_name == "researcher"


def test_openai_agents_simple_goals_from_instructions():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    # 2 agents = 2 goals
    assert len(result.intent.goals) == 2
    descriptions = [g.description.lower() for g in result.intent.goals]
    assert any("research" in d for d in descriptions)
    assert any("writer" in d or "content" in d for d in descriptions)


def test_openai_agents_simple_tools_extracted():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    assert "web_search" in tool_names
    assert "file_reader" in tool_names
    assert "markdown_editor" in tool_names


def test_openai_agents_simple_tools_no_duplicates():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    assert len(tool_names) == len(set(tool_names))


def test_openai_agents_simple_constraints_from_input_guardrails():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    # 2 agents with input guardrails = 2 constraints (1 per agent in simple)
    assert len(result.intent.constraints) >= 2
    rules = [c.rule for c in result.intent.constraints]
    assert any("researcher" in r.lower() for r in rules)
    assert any("writer" in r.lower() for r in rules)


def test_openai_agents_simple_non_negotiables_from_output_guardrails():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    # 2 agents with output guardrails = 3 non-negotiables (2 for researcher, 1 for writer)
    assert len(result.intent.non_negotiables) >= 2
    rules = [nn.rule for nn in result.intent.non_negotiables]
    assert any("researcher" in r.lower() for r in rules)
    assert any("writer" in r.lower() for r in rules)


def test_openai_agents_simple_non_negotiables_severity():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    for nn in result.intent.non_negotiables:
        assert nn.severity == "hard"


def test_openai_agents_simple_boundaries():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    # 2 agents without handoffs = 2 boundaries (one per agent)
    assert len(result.intent.boundaries) == 2


def test_openai_agents_simple_first_agent_high_priority():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    assert result.intent.goals[0].priority == "high"


def test_openai_agents_simple_escalation():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    assert result.intent.escalation is not None
    assert "guardrail" in result.intent.escalation.trigger.lower() or "handoff" in result.intent.escalation.trigger.lower()


def test_openai_agents_simple_failure_modes():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    assert len(result.intent.failure_modes) >= 2


def test_openai_agents_simple_metadata_tags():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    assert "openai-agents" in result.intent.metadata.tags
    assert "imported" in result.intent.metadata.tags


# --- OpenAI Agents adapter: complex fixture ---------------------------------

def test_openai_agents_complex_agent_name():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    assert result.intent.agent_name == "devops-orchestrator"


def test_openai_agents_complex_goals_count():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    assert len(result.intent.goals) == 5


def test_openai_agents_complex_tools_no_duplicates():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    # pagerduty_api appears in Monitor Agent and Incident Responder
    assert tool_names.count("pagerduty_api") == 1
    assert len(tool_names) == len(set(tool_names))


def test_openai_agents_complex_tools_from_dict_format():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    assert "prometheus_api" in tool_names
    assert "kubernetes_api" in tool_names
    assert "vulnerability_scanner" in tool_names


def test_openai_agents_complex_constraints_count():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    # 5 agents with input guardrails (2 each for most) = multiple constraints
    assert len(result.intent.constraints) >= 5


def test_openai_agents_complex_non_negotiables_count():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    # 5 agents with output guardrails = multiple non-negotiables
    assert len(result.intent.non_negotiables) >= 5


def test_openai_agents_complex_boundaries_from_handoffs():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    # Monitor Agent has 2 handoffs, Deploy Agent has 1, Incident Responder has 1,
    # Documentation Agent has 0 (empty list = 1 boundary), Security Reviewer has 1
    # Total: 2 + 1 + 1 + 1 + 1 = 6
    assert len(result.intent.boundaries) >= 5
    # Check that handoff boundaries mention target agents
    scopes = [b.scope for b in result.intent.boundaries]
    assert any("deploy agent" in s.lower() for s in scopes)
    assert any("incident responder" in s.lower() for s in scopes)


def test_openai_agents_complex_description_from_workflow():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    desc = result.intent.agent_description.lower()
    assert "devops" in desc or "multi-agent" in desc or "5 agents" in desc


def test_openai_agents_complex_description_truncated():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    assert len(result.intent.agent_description) <= 200


# --- OpenAI Agents adapter: minimal fixture ---------------------------------

def test_openai_agents_minimal_agent_name():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "minimal.yaml")
    assert result.intent.agent_name == "simple-assistant"


def test_openai_agents_minimal_single_goal():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "minimal.yaml")
    assert len(result.intent.goals) == 1
    assert "helpful" in result.intent.goals[0].description.lower() or "assistant" in result.intent.goals[0].description.lower()


def test_openai_agents_minimal_no_tools():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "minimal.yaml")
    assert len(result.intent.tools_allowed) == 0


def test_openai_agents_minimal_no_constraints():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "minimal.yaml")
    assert len(result.intent.constraints) == 0


def test_openai_agents_minimal_no_non_negotiables():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "minimal.yaml")
    assert len(result.intent.non_negotiables) == 0


def test_openai_agents_minimal_single_boundary():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "minimal.yaml")
    # 1 agent without handoffs = 1 boundary
    assert len(result.intent.boundaries) == 1


def test_openai_agents_minimal_no_warnings():
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "minimal.yaml")
    assert len(result.warnings) == 0


# --- Format detection -------------------------------------------------------

def test_detect_format_openai_agents_by_name(tmp_path):
    """Files named openai-agents.yaml should be detected as openai_agents format."""
    p = tmp_path / "openai-agents.yaml"
    p.write_text("agents: []\n", encoding="utf-8")
    assert detect_format(p) == "openai_agents"


def test_detect_format_openai_agents_yml(tmp_path):
    """Files named openai-agents.yml should be detected as openai_agents format."""
    p = tmp_path / "openai-agents.yml"
    p.write_text("agents: []\n", encoding="utf-8")
    assert detect_format(p) == "openai_agents"


def test_detect_format_openai_agents_non_matching():
    """Files not named openai-agents should not be detected as openai_agents."""
    fmt = detect_format(OA_FIXTURES / "simple.yaml")
    # "simple.yaml" doesn't match "openai-agents" filename pattern
    assert fmt == "agents_md"


# --- Converter pipeline integration ----------------------------------------

def test_converter_parse_dispatch_openai_agents():
    from intentspec.converter import parse
    result = parse(OA_FIXTURES / "simple.yaml", format="openai_agents")
    assert result.format == "openai_agents"
    assert result.intent.agent_name


def test_converter_parse_forced_format_overrides_detection():
    from intentspec.converter import parse
    # Even though "simple.yaml" would be detected as agents_md,
    # forcing format="openai_agents" should use the openai_agents parser
    result = parse(OA_FIXTURES / "simple.yaml", format="openai_agents")
    assert result.format == "openai_agents"


# --- Error handling ---------------------------------------------------------

def test_openai_agents_missing_file():
    from intentspec.adapters.openai_agents import parse_openai_agents
    with pytest.raises(FileNotFoundError):
        parse_openai_agents("/nonexistent/openai-agents.yaml")


def test_openai_agents_invalid_yaml(tmp_path):
    from intentspec.adapters.openai_agents import parse_openai_agents
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("{{invalid: yaml: content: [", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_openai_agents(bad_file)


def test_openai_agents_empty_file(tmp_path):
    from intentspec.adapters.openai_agents import parse_openai_agents
    empty_file = tmp_path / "empty.yaml"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_openai_agents(empty_file)


def test_openai_agents_list_top_level(tmp_path):
    from intentspec.adapters.openai_agents import parse_openai_agents
    list_file = tmp_path / "list.yaml"
    list_file.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected YAML mapping"):
        parse_openai_agents(list_file)


def test_openai_agents_no_agents_warning(tmp_path):
    from intentspec.adapters.openai_agents import parse_openai_agents
    no_agents_file = tmp_path / "noagents.yaml"
    no_agents_file.write_text("workflow:\n  name: empty\n", encoding="utf-8")
    result = parse_openai_agents(no_agents_file)
    assert any("No agents" in w for w in result.warnings)
    # Should still have a default goal
    assert len(result.intent.goals) == 1
    assert result.intent.goals[0].priority == "high"


# --- CLI integration --------------------------------------------------------

def test_cli_init_from_openai_agents():
    """Test that the CLI accepts --from openai_agents."""
    from click.testing import CliRunner
    from intentspec.cli import init
    runner = CliRunner()
    with runner.isolated_filesystem():
        import shutil
        src = OA_FIXTURES / "simple.yaml"
        dst = Path("simple.yaml")
        shutil.copy2(src, dst)
        result = runner.invoke(init, ["--from", "openai_agents", "--name", "test-oa", "--yes", "simple.yaml"])
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert Path("intent.yaml").exists()


# --- Edge cases -------------------------------------------------------------

def test_openai_agents_tool_rationale():
    """Tools should reference which agent uses them."""
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    for tool in result.intent.tools_allowed:
        assert "Used by agent:" in tool.rationale


def test_openai_agents_constraint_enforceable():
    """Constraints from input guardrails should be enforceable."""
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    for constraint in result.intent.constraints:
        assert constraint.enforceable is True


def test_openai_agents_multi_agent_description():
    """Multi-agent configs should mention agent count in description."""
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    desc = result.intent.agent_description.lower()
    assert "2 agents" in desc or "openai" in desc


def test_openai_agents_goal_priority_second_agent():
    """Second agent should have medium priority."""
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    assert result.intent.goals[1].priority == "medium"


def test_openai_agents_escalation_fields():
    """Escalation should have both trigger and method."""
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    assert result.intent.escalation.trigger
    assert result.intent.escalation.method


def test_openai_agents_failure_modes_have_mitigation():
    """All failure modes should have mitigation text."""
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    for fm in result.intent.failure_modes:
        assert fm.mode
        assert fm.mitigation


def test_openai_agents_boundaries_have_scope_and_out():
    """All boundaries should have scope and out_of_scope."""
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "simple.yaml")
    for boundary in result.intent.boundaries:
        assert boundary.scope
        assert boundary.out_of_scope


def test_openai_agents_handoff_boundary_contains_target():
    """Handoff boundaries should mention the target agent."""
    from intentspec.adapters.openai_agents import parse_openai_agents
    result = parse_openai_agents(OA_FIXTURES / "complex.yaml")
    scopes = [b.scope for b in result.intent.boundaries]
    # Monitor Agent hands off to Deploy Agent and Incident Responder
    assert any("deploy agent" in s.lower() for s in scopes)
    assert any("incident responder" in s.lower() for s in scopes)
