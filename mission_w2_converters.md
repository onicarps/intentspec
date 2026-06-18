# Mission: IntentSpec Week 2 — Converters

## Your Task
Review this mission brief for viability, then implement Week 2 of the IntentSpec project: the converter module that transforms existing agent specs (AGENTS.md, SKILL.md) into structured intent.yaml files.

## Context: What Was Built in Week 1

The following already exists and works (28 tests passing):
- `pyproject.toml` — package config, Click/PyYAML/jsonschema/pytest deps
- `src/intentspec/models/intent.py` — Intent dataclass with sub-models (Goal, Constraint, NonNegotiable, ToolPermission, Boundary, Escalation, FailureMode, AgentMetadata), from_file/from_dict/to_dict/to_yaml methods
- `src/intentspec/spec/schema.py` — Complete JSON Schema v1 (INTENT_SCHEMA_V1) with types, enums, patterns, constraints
- `src/intentspec/spec/validate.py` — Schema validation (jsonschema Draft7) + semantic validation (duplicates, overlaps, missing rationale, short descriptions) with helpful hint messages
- `src/intentspec/spec/formatter.py` — Terminal output formatter with ANSI color support
- `src/intentspec/cli.py` — Click CLI with `validate` command (--format text/json/yaml, --strict), stubs for score/coverage/init/diff/ci/audit-report/lint
- `tests/fixtures/valid_intent.yaml` — Full valid example
- `tests/fixtures/invalid_intent.yaml` — Invalid example
- `tests/test_validate.py` — 28 tests, all passing

## What Week 2 Needs to Build

### 1. AGENTS.md Parser (`src/intentspec/converter/agents_md.py`)
Parse AGENTS.md files and extract structured intent. Use regex + heuristics:
- Extract agent name from H1/H2 headers ("# Agent Name" or "# You are...")
- Extract goals from sections like "## Goals", "## Purpose", "## What you do"
- Extract constraints from "NEVER", "MUST NOT", "Do NOT", "Always", "Must" patterns
- Extract non-negotiables from emphatic language ("Under no circumstances", "Never ever")
- Extract tools from code blocks, tables, or bullet lists mentioning tool/API names
- Extract boundaries from "## Boundaries", "## Scope", "## Limitations" sections
- Handle edge cases: empty files, no agent definition, multiple agents, non-English

### 2. SKILL.md Parser (`src/intentspec/converter/skill_md.py`)
Parse agentskills SKILL.md format:
- YAML frontmatter: name, description, version, tags → agent.name, agent.description, metadata.tags
- Markdown body: Overview → goals/executive summary, Instructions → constraints, Notes → non-negotiables

### 3. LLM-based Extraction (`src/intentspec/converter/llm_extract.py`)
For ambiguous sections that regex can't handle:
- Use OpenRouter API (urllib, no extra deps)
- Opt-in only (user must pass --use-llm flag)
- Cache results locally to avoid re-extracting
- Graceful fallback to rule-based on API failure
- Document cost estimates

### 4. Interactive Converter (`src/intentspec/converter/interactive.py`)
Review flow after extraction:
- Show extracted intent with color-coded confidence (green=high, yellow=medium, red=low/missing)
- Prompt user to confirm/correct each field
- --interactive flag (default for --from commands), --yes to skip
- Per-field confidence scores in output comments

### 5. Quickstart Wizard (`src/intentspec/converter/quickstart.py`)
3 interactive questions → minimal intent.yaml:
1. "What does the agent do?" → goals
2. "What must it never do?" → non_negotiables (severity: hard)
3. "What tools does it use?" → tools.allowed

### 6. Converter Accuracy Benchmark (`tests/benchmark_converter.py`)
CI benchmark test:
- Run converter against 20 real AGENTS.md/SKILL.md files from spike
- Measure field-level accuracy (precision/recall per field)
- Target: 75%+ for v1, 85%+ for v1.1
- Fail CI if below threshold

### 7. CLI Integration (update `src/intentspec/cli.py`)
Wire up the init command:
- `intentspec init --from AGENTS.md` → parse → extract → interactive review → write intent.yaml
- `intentspec init --from SKILL.md` → same
- `intentspec init --from agentskills` → same
- `intentspec init --quickstart` → wizard → write intent.yaml
- Support --format text/json/yaml, --yes, --interactive/--no-interactive

### 8. Tests (`tests/test_converter.py`)
- Test AGENTS.md parser against 5+ real files
- Test SKILL.md parser against 3+ real files
- Test interactive flow (mocked input)
- Test quickstart wizard
- Test edge cases: empty, malformed, non-English, recursive refs
- Test converter accuracy benchmark

## Rules
1. Follow TDD: write each test before its source file
2. Commit after each file with message: "feat(converter): <description>"
3. All code must pass linting (Python 3.12, no external deps beyond stdlib+Click+PyYAML+jsonschema)
4. Target: 80%+ coverage for converter module
5. All commands must work end-to-end before marking complete
6. Use yaml.safe_load() everywhere, never yaml.load()
7. Handle encoding issues (UTF-8, BOM, Unicode)

## Viability Review
Before implementing, assess:
1. Is the Week 2 scope realistic for a mission? (~16h of work)
2. Are there any blockers from Week 1 that need fixing first?
3. What's the riskiest part of this mission?
4. What should be the acceptance criteria?

Report your viability assessment before starting implementation.
