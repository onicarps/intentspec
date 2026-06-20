# Format Validation Report

**Date:** June 20, 2026
**Schema:** intent.yaml v1.0
**Fixtures tested:** 5 real-world agent configs

## Summary

All 5 real-world agent configurations were successfully parsed and validated against the IntentSpec v1 schema. No schema changes were required.

## Fixtures Tested

| # | Fixture | Format | Source Pattern |
|---|---------|--------|----------------|
| 1 | `autogpt_coding_agent.md` | AGENTS.md | AutoGPT-style coding review agent |
| 2 | `research_skill.md` | SKILL.md | Data research skill with YAML frontmatter |
| 3 | `crewai.yaml` | CrewAI | Multi-agent setup (Researcher, Writer, Reviewer) |
| 4 | `langgraph.yaml` | LangGraph | Customer support graph with state schema |
| 5 | `openai-agents.yaml` | OpenAI Agents SDK | DevOps agent with guardrails and handoffs |

## Findings

### 1. AGENTS.md Tool Extraction
**Finding:** Tools must be wrapped in backticks (code spans) for extraction from prose sections.
**Status:** Working as designed. The parser uses `_RE_CODE_SPAN` to identify tool names in prose.
**Recommendation:** Document this requirement in the schema reference.

### 2. SKILL.md Frontmatter Detection
**Finding:** The file must begin with `---` (YAML frontmatter) to be detected as `skill_md`. Files with content before frontmatter are detected as `agents_md`.
**Status:** Working as designed. This is intentional — SKILL.md files should start with frontmatter.
**Recommendation:** Document this requirement.

### 3. LangGraph State Schema
**Finding:** The adapter expects `state.schema.fields` (nested dict), not `state.schema` (direct list).
**Status:** Fixed in fixture. The adapter's expected format is `state.schema.fields: [{name, type, description}]`.
**Recommendation:** This matches the LangGraph Python API's `StateGraph` pattern.

### 4. OpenAI Agents Guardrails
**Finding:** Guardrails (input/output filters) are correctly mapped to constraints and non-negotiables.
**Status:** Working correctly.

### 5. OpenAI Agents Handoffs
**Finding:** Handoffs are correctly mapped to boundaries with scope and out_of_scope.
**Status:** Working correctly.

### 6. CrewAI Delegation
**Finding:** `allow_delegation` flag is correctly mapped to boundaries.
**Status:** Working correctly.

## Schema Coverage

All v1 schema fields are covered by at least one fixture:

| Field | Covered By |
|-------|-----------|
| `agent.name` | All fixtures |
| `agent.type` | All fixtures |
| `agent.description` | All fixtures |
| `intent.goals` | All fixtures |
| `intent.constraints` | AGENTS.md, SKILL.md, LangGraph, OpenAI Agents |
| `intent.non_negotiables` | AGENTS.md, OpenAI Agents |
| `intent.tools.allowed` | AGENTS.md, CrewAI, LangGraph, OpenAI Agents |
| `intent.tools.denied` | AGENTS.md, OpenAI Agents |
| `intent.boundaries` | CrewAI, LangGraph, OpenAI Agents |
| `intent.escalation` | LangGraph, OpenAI Agents |
| `intent.failure_modes` | LangGraph, OpenAI Agents |
| `metadata.status` | Schema coverage test |
| `metadata.owner` | Schema coverage test |
| `metadata.tags` | SKILL.md, LangGraph, OpenAI Agents |

## Recommendations

1. **Document tool format requirement:** AGENTS.md tools should use backtick-wrapped names in prose sections.
2. **Document SKILL.md frontmatter requirement:** File must start with `---`.
3. **Consider adding a "Tools" section parser** that also extracts tools from plain text (not just backtick-wrapped) for better real-world compatibility.
4. **Consider adding a "description" field** to the agent model for longer descriptions (currently truncated to 200 chars).

## Test Results

```
tests/test_format_validation.py::TestRealWorldFixtures::test_autogpt_coding_agent_exists PASSED
tests/test_format_validation.py::TestRealWorldFixtures::test_research_skill_exists PASSED
tests/test_format_validation.py::TestRealWorldFixtures::test_crewai_multi_agent_exists PASSED
tests/test_format_validation.py::TestRealWorldFixtures::test_langgraph_support_agent_exists PASSED
tests/test_format_validation.py::TestRealWorldFixtures::test_openai_agents_devops_exists PASSED
tests/test_format_validation.py::TestAutogptCodingAgent::test_parse_autogpt_coding_agent PASSED
tests/test_format_validation.py::TestAutogptCodingAgent::test_autogpt_goals_have_priorities PASSED
tests/test_format_validation.py::TestAutogptCodingAgent::test_autogpt_constraints_have_enforceable PASSED
tests/test_format_validation.py::TestAutogptCodingAgent::test_autogpt_schema_valid PASSED
tests/test_format_validation.py::TestResearchSkill::test_parse_research_skill PASSED
tests/test_format_validation.py::TestResearchSkill::test_research_skill_schema_valid PASSED
tests/test_format_validation.py::TestCrewaiMultiAgent::test_parse_crewai_multi_agent PASSED
tests/test_format_validation.py::TestCrewaiMultiAgent::test_crewai_schema_valid PASSED
tests/test_format_validation.py::TestLanggraphSupportAgent::test_parse_langgraph_support_agent PASSED
tests/test_format_validation.py::TestLanggraphSupportAgent::test_langgraph_schema_valid PASSED
tests/test_format_validation.py::TestLanggraphSupportAgent::test_langgraph_state_fields_extracted PASSED
tests/test_format_validation.py::TestOpenAIAgentsDevops::test_parse_openai_agents_devops PASSED
tests/test_format_validation.py::TestOpenAIAgentsDevops::test_openai_agents_schema_valid PASSED
tests/test_format_validation.py::TestOpenAIAgentsDevops::test_openai_agents_guardrails_as_constraints PASSED
tests/test_format_validation.py::TestOpenAIAgentsDevops::test_openai_agents_handoffs_as_boundaries PASSED
tests/test_format_validation.py::TestSchemaCoverage::test_all_standard_fields_parseable PASSED
tests/test_format_validation.py::TestSchemaGaps::test_multiline_instructions_handled PASSED
tests/test_format_validation.py::TestSchemaGaps::test_crewai_delegation_flag PASSED

23 passed
```
