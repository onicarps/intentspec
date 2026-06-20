"""Format validation — test schema against real-world agent configs.

Validates that the v1 schema and converters can handle real-world patterns
found in popular agent frameworks (AutoGPT, CrewAI, LangGraph, OpenAI Agents SDK).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from intentspec.converter import parse
from intentspec.converter.types import ConverterError
from intentspec.spec.validate import validate_file

FIXTURES = Path(__file__).parent / "fixtures" / "real_world"


# --- Fixture Tests ---

class TestRealWorldFixtures:
    """Test that all real-world fixtures exist and are parseable."""

    def test_autogpt_coding_agent_exists(self):
        assert (FIXTURES / "autogpt_coding_agent.md").exists()

    def test_research_skill_exists(self):
        assert (FIXTURES / "research_skill.md").exists()

    def test_crewai_multi_agent_exists(self):
        assert (FIXTURES / "crewai.yaml").exists()

    def test_langgraph_support_agent_exists(self):
        assert (FIXTURES / "langgraph.yaml").exists()

    def test_openai_agents_devops_exists(self):
        assert (FIXTURES / "openai-agents.yaml").exists()


# --- AGENTS.md Conversion ---

class TestAutogptCodingAgent:
    """Test AGENTS.md → intent.yaml conversion with real-world coding agent."""

    def test_parse_autogpt_coding_agent(self):
        result = parse(str(FIXTURES / "autogpt_coding_agent.md"))
        assert result.format == "agents_md"
        assert result.intent.agent_name
        assert len(result.intent.goals) >= 3
        assert len(result.intent.constraints) >= 4
        assert len(result.intent.non_negotiables) >= 3
        assert len(result.intent.tools_allowed) >= 2

    def test_autogpt_goals_have_priorities(self):
        result = parse(str(FIXTURES / "autogpt_coding_agent.md"))
        for goal in result.intent.goals:
            assert goal.priority in ("high", "medium", "low")

    def test_autogpt_constraints_have_enforceable(self):
        result = parse(str(FIXTURES / "autogpt_coding_agent.md"))
        for constraint in result.intent.constraints:
            assert constraint.enforceable is not None

    def test_autogpt_schema_valid(self):
        result = parse(str(FIXTURES / "autogpt_coding_agent.md"))
        data = result.intent.to_dict()
        # Should not raise
        from intentspec.spec.validate import validate_schema
        errors = validate_schema(data)
        assert len(errors) == 0, f"Schema errors: {errors}"


# --- SKILL.md Conversion ---

class TestResearchSkill:
    """Test SKILL.md → intent.yaml conversion with real-world research skill."""

    def test_parse_research_skill(self):
        result = parse(str(FIXTURES / "research_skill.md"))
        assert result.format == "skill_md"
        assert result.intent.agent_name
        assert len(result.intent.goals) >= 2

    def test_research_skill_schema_valid(self):
        result = parse(str(FIXTURES / "research_skill.md"))
        from intentspec.spec.validate import validate_schema
        errors = validate_schema(result.intent.to_dict())
        assert len(errors) == 0, f"Schema errors: {errors}"


# --- CrewAI Conversion ---

class TestCrewaiMultiAgent:
    """Test crewai.yaml → intent.yaml conversion with real-world multi-agent setup."""

    def test_parse_crewai_multi_agent(self):
        result = parse(str(FIXTURES / "crewai.yaml"))
        assert result.format == "crewai"
        assert result.intent.agent_name
        # Multi-agent setup should produce goals from tasks
        assert len(result.intent.goals) >= 2
        # Should extract tools from all agents
        assert len(result.intent.tools_allowed) >= 3

    def test_crewai_schema_valid(self):
        result = parse(str(FIXTURES / "crewai.yaml"))
        from intentspec.spec.validate import validate_schema
        errors = validate_schema(result.intent.to_dict())
        assert len(errors) == 0, f"Schema errors: {errors}"


# --- LangGraph Conversion ---

class TestLanggraphSupportAgent:
    """Test langgraph.yaml → intent.yaml conversion with real-world support agent."""

    def test_parse_langgraph_support_agent(self):
        result = parse(str(FIXTURES / "langgraph.yaml"))
        assert result.format == "langgraph"
        assert result.intent.agent_name
        # Should extract goals from node descriptions
        assert len(result.intent.goals) >= 1

    def test_langgraph_schema_valid(self):
        result = parse(str(FIXTURES / "langgraph.yaml"))
        from intentspec.spec.validate import validate_schema
        errors = validate_schema(result.intent.to_dict())
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_langgraph_state_fields_extracted(self):
        """LangGraph state schema fields should become constraints."""
        result = parse(str(FIXTURES / "langgraph.yaml"))
        # State fields: conversation_history, customer_id, intent, escalation_count, satisfaction_score
        # Should be extracted as constraints
        assert len(result.intent.constraints) >= 3
        # Agent name comes from first node
        assert result.intent.agent_name == "intent-classifier"


# --- OpenAI Agents Conversion ---

class TestOpenAIAgentsDevops:
    """Test openai-agents.yaml → intent.yaml conversion with real-world DevOps agent."""

    def test_parse_openai_agents_devops(self):
        result = parse(str(FIXTURES / "openai-agents.yaml"))
        assert result.format == "openai_agents"
        assert result.intent.agent_name
        # Should extract goals from instructions
        assert len(result.intent.goals) >= 1

    def test_openai_agents_schema_valid(self):
        result = parse(str(FIXTURES / "openai-agents.yaml"))
        from intentspec.spec.validate import validate_schema
        errors = validate_schema(result.intent.to_dict())
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_openai_agents_guardrails_as_constraints(self):
        """OpenAI guardrails should map to constraints or non-negotiables."""
        result = parse(str(FIXTURES / "openai-agents.yaml"))
        # Should have extracted some constraints from guardrails
        total = len(result.intent.constraints) + len(result.intent.non_negotiables)
        assert total >= 1, "Expected guardrails to produce constraints or non-negotiables"

    def test_openai_agents_handoffs_as_boundaries(self):
        """OpenAI handoffs should map to boundaries."""
        result = parse(str(FIXTURES / "openai-agents.yaml"))
        # Should have extracted boundaries from handoffs
        assert len(result.intent.boundaries) >= 1


# --- Schema Coverage Tests ---

class TestSchemaCoverage:
    """Test that the schema covers all fields found in real-world configs."""

    def test_all_standard_fields_parseable(self, tmp_path):
        """Create a comprehensive spec with all standard fields and validate."""
        spec = tmp_path / "full_spec.yaml"
        spec.write_text("""version: "1.0"
agent:
  name: "full-test-agent"
  type: "coding"
  description: "A comprehensive test agent with all fields populated"
intent:
  goals:
    - description: "Achieve primary objective with high quality"
      priority: "high"
      success_criteria: "All tests pass and coverage > 90%"
    - description: "Provide helpful responses"
      priority: "medium"
  constraints:
    - rule: "Never modify production without approval"
      enforceable: true
    - rule: "Follow style guide"
      enforceable: false
    - rule: "Always log actions"
      enforceable: true
  non_negotiables:
    - rule: "Never leak customer data"
      severity: "hard"
    - rule: "Prefer human review for sensitive operations"
      severity: "soft"
  tools:
    allowed:
      - name: "github_api"
        rationale: "Required for code review and PR management"
      - name: "code_analyzer"
        rationale: "Static analysis and security scanning"
    denied:
      - name: "production_deployer"
        rationale: "Deployments require human approval"
  boundaries:
    - scope: "Code review and development tasks"
      out_of_scope: "Production deployments, database migrations, infrastructure changes"
  escalation:
    trigger: "Security incident or production outage"
    method: "Page on-call engineer and create incident ticket"
  failure_modes:
    - mode: "Approves code with subtle bugs"
      mitigation: "Require human sampling of approvals"
    - mode: "Becomes overly permissive"
      mitigation: "Monthly calibration reviews"
metadata:
  status: "active"
  owner: "team@example.com"
  review_cycle: "monthly"
  tags: ["coding", "review", "security"]
""")
        # Should parse and validate without errors
        result = validate_file(spec)
        intent, errors, warnings = result
        assert len(errors) == 0, f"Validation errors: {errors}"
        assert intent.agent_name == "full-test-agent"
        assert len(intent.goals) == 2
        assert len(intent.constraints) == 3
        assert len(intent.non_negotiables) == 2
        assert len(intent.tools_allowed) == 2
        assert len(intent.tools_denied) == 1
        assert len(intent.boundaries) == 1
        assert intent.escalation is not None
        assert len(intent.failure_modes) == 2


# --- Schema Gap Analysis ---

class TestSchemaGaps:
    """Document any schema gaps found during validation."""

    def test_multiline_instructions_handled(self):
        """OpenAI Agents SDK uses multiline instructions strings."""
        # This is a real-world pattern that should work
        content = {
            "agents": [{
                "name": "test",
                "instructions": "Line 1\nLine 2\nLine 3"
            }]
        }
        # Should not crash when parsing
        from intentspec.adapters.openai_agents import parse_openai_agents
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(content, f)
            path = f.name
        try:
            result = parse_openai_agents(path)
            assert result.intent.agent_name
        finally:
            os.unlink(path)

    def test_crewai_delegation_flag(self):
        """CrewAI allow_delegation should map to boundaries."""
        content = {
            "agents": [
                {"role:": "Manager", "backstory": "manages", "allow_delegation": True},
                {"role:": "Worker", "backstory": "works", "allow_delegation": False},
            ]
        }
        from intentspec.adapters.crewai import parse_crewai
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            yaml.dump(content, f)
            path = f.name
        try:
            result = parse_crewai(path)
            assert len(result.intent.boundaries) >= 2
        finally:
            os.unlink(path)
