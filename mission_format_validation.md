# Mission: Format Validation — Test Schema with Real Agent Configs

## Your Task
Validate the IntentSpec v1 schema against 5+ real-world agent configurations from popular open-source projects. Find schema gaps, iterate if needed, and document findings.

## Context
- Schema: `src/intentspec/spec/schema.py` — JSON Schema v1 for intent.yaml
- Model: `src/intentspec/models/intent.py` — Intent dataclass
- Validator: `src/intentspec/spec/validate.py` — schema + semantic validation
- Existing fixtures: `tests/fixtures/` — valid_intent.yaml, invalid_intent.yaml, sample_agents_md/, sample_skills_md/, sample_agentskills/, sample_crewai/, sample_langgraph/, sample_autogen/, sample_openai_agents/

## What To Do

### 1. Find Real Agent Configs
Search GitHub for real AGENTS.md, SKILL.md, and agent config files from popular projects. Look for:
- AGENTS.md files in open-source AI agent repos (e.g., AutoGPT, CrewAI examples, LangGraph examples)
- SKILL.md files from the agentskills ecosystem
- Real crewai.yaml, langgraph.yaml configs

Use `web_search` to find them. Download or create representative fixtures.

### 2. Create Test Fixtures
For each real config found, create a fixture in `tests/fixtures/real_world/`:
- `project-name_source.md` — the original source file
- `project-name_expected.yaml` — the expected intent.yaml output (or partial)

Aim for at least 5 diverse real-world configs covering:
- A coding agent (e.g., from a code review bot project)
- A research agent (e.g., from a data analysis project)
- A multi-agent setup (e.g., from a CrewAI or LangGraph project)
- A service/support agent
- A data pipeline agent

### 3. Validate Against Schema
For each fixture:
- Parse it using the appropriate converter (`parse_agents_md`, `parse_skill_md`, etc.)
- Validate the output against the schema
- Run semantic validation
- Document any fields that fail validation or are missing

### 4. Iterate Schema if Needed
If real-world configs reveal schema gaps:
- Update `src/intentspec/spec/schema.py` to accommodate valid real-world patterns
- Update `src/intentspec/models/intent.py` if new fields are needed
- Update converters if extraction patterns need adjustment
- Ensure all existing tests still pass

### 5. Document Findings
Create `FORMAT_VALIDATION.md` in the workspace root documenting:
- Which real-world configs were tested
- What schema issues were found (if any)
- What changes were made to the schema/converters
- Recommendations for future schema evolution

## Constraints
- No new runtime dependencies
- All existing tests must pass: `python3 -m pytest tests/ -q`
- Type hints, Google-style docstrings on any new code
- Follow existing patterns from converters and fixtures

## Verification
```bash
cd ~/.hermes/profiles/intentspec/workspace
python3 -m pytest tests/ -q
python3 -m intentspec validate tests/fixtures/real_world/
```
