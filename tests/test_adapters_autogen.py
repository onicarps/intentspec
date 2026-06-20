"""Tests for the AutoGen adapter."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from intentspec.converter.format_detect import detect_format
from intentspec.converter.types import ConverterError

AG_FIXTURES = Path(__file__).parent / "fixtures" / "sample_autogen"


# --- AutoGen adapter: simple fixture ----------------------------------------

def test_autogen_simple_produces_valid_intent():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    assert result.intent.agent_name
    assert result.intent.agent_type == "custom"
    assert result.intent.goals
    assert result.format == "autogen"


def test_autogen_simple_agent_name():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    assert result.intent.agent_name == "content-generator"


def test_autogen_simple_goals_from_agents():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    # 2 agents = 2 goals
    assert len(result.intent.goals) == 2
    descriptions = [g.description.lower() for g in result.intent.goals]
    assert any("research" in d for d in descriptions)
    assert any("write" in d or "writer" in d for d in descriptions)


def test_autogen_simple_tools_extracted():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    assert "web_search" in tool_names
    assert "rss_reader" in tool_names
    assert "markdown_editor" in tool_names


def test_autogen_simple_tools_no_duplicates():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    assert len(tool_names) == len(set(tool_names))


def test_autogen_simple_constraints_from_system_message():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    # 2 agents with system_message = 2 constraints
    assert len(result.intent.constraints) == 2
    rules = [c.rule for c in result.intent.constraints]
    assert any("researcher" in r for r in rules)
    assert any("writer" in r for r in rules)


def test_autogen_simple_boundaries_from_human_input_mode():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    # 2 agents = 2 boundaries
    assert len(result.intent.boundaries) == 2


def test_autogen_simple_first_agent_high_priority():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    assert result.intent.goals[0].priority == "high"


def test_autogen_simple_escalation():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    assert result.intent.escalation is not None
    assert "max" in result.intent.escalation.trigger.lower() or "round" in result.intent.escalation.trigger.lower()


def test_autogen_simple_failure_modes():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    assert len(result.intent.failure_modes) >= 2


def test_autogen_simple_metadata_tags():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    assert "autogen" in result.intent.metadata.tags
    assert "imported" in result.intent.metadata.tags


# --- AutoGen adapter: complex fixture ---------------------------------------

def test_autogen_complex_agent_name():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "complex.yaml")
    assert result.intent.agent_name == "devops-orchestrator"


def test_autogen_complex_goals_count():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "complex.yaml")
    assert len(result.intent.goals) == 5


def test_autogen_complex_tools_no_duplicates():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "complex.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    # pagerduty_api appears in monitor_agent and incident_responder
    assert tool_names.count("pagerduty_api") == 1
    assert len(tool_names) == len(set(tool_names))


def test_autogen_complex_tools_from_dict_format():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "complex.yaml")
    tool_names = [t.name for t in result.intent.tools_allowed]
    # Tools are in dict format with "name" key
    assert "prometheus_api" in tool_names
    assert "kubernetes_api" in tool_names
    assert "vulnerability_scanner" in tool_names


def test_autogen_complex_constraints_count():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "complex.yaml")
    # 5 agents with system_message = 5 constraints
    assert len(result.intent.constraints) == 5


def test_autogen_complex_boundaries():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "complex.yaml")
    # 5 agents = 5 boundaries
    assert len(result.intent.boundaries) == 5


def test_autogen_complex_description_truncated():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "complex.yaml")
    assert len(result.intent.agent_description) <= 200


# --- AutoGen adapter: minimal fixture ---------------------------------------

def test_autogen_minimal_agent_name():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "minimal.yaml")
    assert result.intent.agent_name == "simple-assistant"


def test_autogen_minimal_single_goal():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "minimal.yaml")
    assert len(result.intent.goals) == 1
    assert "answer" in result.intent.goals[0].description.lower()


def test_autogen_minimal_single_constraint():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "minimal.yaml")
    # 1 agent with system_message = 1 constraint
    assert len(result.intent.constraints) == 1


def test_autogen_minimal_no_tools():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "minimal.yaml")
    assert len(result.intent.tools_allowed) == 0


def test_autogen_minimal_no_warnings():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "minimal.yaml")
    assert len(result.warnings) == 0


# --- Format detection -------------------------------------------------------

def test_detect_format_autogen_by_name(tmp_path):
    """Files named autogen-config.yaml should be detected as autogen format."""
    from intentspec.converter.format_detect import detect_format
    # Create a file named autogen-config.yaml
    p = tmp_path / "autogen-config.yaml"
    p.write_text("agents: []\n", encoding="utf-8")
    assert detect_format(p) == "autogen"


def test_detect_format_autogen_yml(tmp_path):
    """Files named autogen-config.yml should be detected as autogen format."""
    from intentspec.converter.format_detect import detect_format
    p = tmp_path / "autogen-config.yml"
    p.write_text("agents: []\n", encoding="utf-8")
    assert detect_format(p) == "autogen"


def test_detect_format_autogen_non_matching():
    """Files not named autogen-config should not be detected as autogen."""
    fmt = detect_format(AG_FIXTURES / "simple.yaml")
    # "simple.yaml" doesn't match "autogen-config" filename pattern
    assert fmt == "agents_md"


# --- Converter pipeline integration -----------------------------------------

def test_converter_parse_dispatch_autogen():
    from intentspec.converter import parse
    result = parse(AG_FIXTURES / "simple.yaml", format="autogen")
    assert result.format == "autogen"
    assert result.intent.agent_name


def test_converter_parse_forced_format_overrides_detection():
    from intentspec.converter import parse
    # Even though "simple.yaml" would be detected as agents_md,
    # forcing format="autogen" should use the autogen parser
    result = parse(AG_FIXTURES / "simple.yaml", format="autogen")
    assert result.format == "autogen"


# --- Error handling ---------------------------------------------------------

def test_autogen_missing_file():
    from intentspec.adapters.autogen import parse_autogen
    with pytest.raises(FileNotFoundError):
        parse_autogen("/nonexistent/autogen-config.yaml")


def test_autogen_invalid_yaml(tmp_path):
    from intentspec.adapters.autogen import parse_autogen
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("{{invalid: yaml: content: [", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_autogen(bad_file)


def test_autogen_empty_file(tmp_path):
    from intentspec.adapters.autogen import parse_autogen
    empty_file = tmp_path / "empty.yaml"
    empty_file.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_autogen(empty_file)


def test_autogen_list_top_level(tmp_path):
    from intentspec.adapters.autogen import parse_autogen
    list_file = tmp_path / "list.yaml"
    list_file.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Expected YAML mapping"):
        parse_autogen(list_file)


def test_autogen_no_agents_warning(tmp_path):
    from intentspec.adapters.autogen import parse_autogen
    no_agents_file = tmp_path / "noagents.yaml"
    no_agents_file.write_text("metadata:\n  name: empty\n", encoding="utf-8")
    result = parse_autogen(no_agents_file)
    assert any("No agents" in w for w in result.warnings)
    # Should still have a default goal
    assert len(result.intent.goals) == 1
    assert result.intent.goals[0].priority == "high"


# --- CLI integration --------------------------------------------------------

def test_cli_init_from_autogen():
    """Test that the CLI accepts --from autogen."""
    from click.testing import CliRunner
    from intentspec.cli import init
    runner = CliRunner()
    with runner.isolated_filesystem():
        import shutil
        src = AG_FIXTURES / "simple.yaml"
        dst = Path("simple.yaml")
        shutil.copy2(src, dst)
        result = runner.invoke(init, ["--from", "autogen", "--name", "test-ag", "--yes", "simple.yaml"])
        assert result.exit_code == 0, f"CLI failed: {result.output}"
        assert Path("intent.yaml").exists()


# --- Edge cases -------------------------------------------------------------

def test_autogen_description_truncated():
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "complex.yaml")
    assert len(result.intent.agent_description) <= 200


def test_autogen_multi_agent_description():
    """Multi-agent configs should mention agent count in description."""
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    assert "2 agents" in result.intent.agent_description.lower() or "autogen" in result.intent.agent_description.lower()


def test_autogen_tool_rationale():
    """Tools should reference which agent uses them."""
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    for tool in result.intent.tools_allowed:
        assert "Used by agent:" in tool.rationale


def test_autogen_constraint_enforceable_false():
    """Constraints from system_message should be non-enforceable (human judgment)."""
    from intentspec.adapters.autogen import parse_autogen
    result = parse_autogen(AG_FIXTURES / "simple.yaml")
    for constraint in result.intent.constraints:
        assert constraint.enforceable is False
