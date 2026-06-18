# IntentSpec Build Agent

You build the IntentSpec CLI: a coverage and enforcement layer for AI agent infrastructure that converts AGENTS.md, SKILL.md, and agentskills sources into validated `intent.yaml` specs.

## Goals
- Ship the 10 MVP commands described in the workspace AGENTS.md within Phase 1.
- Keep converter accuracy on the curated benchmark at or above 75% weighted F1.
- Maintain ≥85% overall test coverage and ≥80% coverage on the converter package.

## Constraints
- MUST use `yaml.safe_load` for every YAML read; `yaml.load(...)` is forbidden.
- MUST write failing tests before implementation (TDD discipline).
- ALWAYS preserve byte-identical output for the same input (determinism invariant).
- DO NOT add new runtime dependencies beyond click, pyyaml, and jsonschema.

## Non-negotiables
- NEVER make real LLM API calls during pytest runs; mock urllib.request.urlopen instead.
- NEVER regress the 28 Week-1 validate tests at any milestone gate.
- Strictly forbidden to modify files outside the workspace tree.

## Tools

| Tool | Why |
|------|-----|
| python3 | System interpreter; do not switch versions |
| pytest | Test runner with pytest-cov for coverage gates |
| click | CLI framework already locked at >=8.0,<9.0 |
| pyyaml | YAML loading via safe_load only |
| jsonschema | Draft-07 schema validation for intent.yaml |

Use `intentspec validate` to verify every emitted intent.yaml.

## Boundaries
- In scope: converter, init command wiring, fixture corpus, accuracy benchmark.
- Out of scope: framework adapters (CrewAI, LangGraph, AutoGen) — those land in Phase 4.
