# Factory Droid Mission Brief — Phase 2A Coding

## Context

IntentSpec v0.1.0 is shipped with 806 tests, 16 commands, 4 framework adapters.
Your task is to implement the code changes described in the updated Phase 2PLAN.
DO NOT implement everything — only the items listed below under "Scope".

## Source of Truth

- Plan: `intentspec/PLAN_PHASE2.md` (read this first for sprint structure)
- Build profile: `AGENTS.md`

## Scope

Implement code support for Phase 2A's 3 sprints. This means:

### Sprint 1: Foundation (code readiness)
1. Schema migration support — The schema already supports v1.0. Add version detection and migration utilities (additive only, no breaking changes):
   - `src/intentspec/migrate.py` — Migrator class with `migrate_v1_0_to_v1_1(content: str) -> str`
   - Detect `version: "1.0"` → add `version: "1.1"` header comment
   - Already v1.1 = no-op
   - Malformed YAML = ValueError with guidance
   - Tests in `tests/test_migrate.py` (all v1.0 fixture files migrate cleanly)
   - Wire `intentspec migrate` command in cli.py

2. Converter accuracy benchmark — Establish the baseline:
   - `tests/benchmark_converter.py` already exists. Verify it works.
   - Run it: `python3 -m pytest tests/benchmark_converter.py -v --tb=short`
   - Report current accuracy on the 20-file benchmark
   - If <70%, improve parsers until ≥75%

### Sprint 2: The Core Moat
3. Converter accuracy improvements (code changes only):
   - Focus on AGENTS.md parser — improve tool extraction, goal detection
   - Improve SKILL.md parser — better section detection
   - Target: ≥75% field-level accuracy on benchmark
   - Add more benchmark fixtures if coverage is low

4. Linting rules engine v2:
   - `src/intentspec/lint/__init__.py` currently has 6 hardcoded rules
   - Expand to 15+ rules. Add rules for:
     - `missing-escalation` — warn if no escalation defined
     - `missing-failure-modes` — warn if no failure modes
     - `missing-boundaries` — warn if no scope/out_of_scope
     - `tools-not-in-source` — tools declared but not mentioned in source text
     - `empty-description` — goals/tools with placeholder text
     - `duplicate-goals` — goals with similar descriptions
     - `unenforceable-constraint` — constraints marked enforceable but not auto-checkable
     - `missing-denied-tools` — no tools.denied section
     - `goal-without-success-criteria` — goals missing measurable criteria
     - `agent-description-length` — description >200 chars
   - Keep rules hardcoded (no plugin interface yet)
   - Each rule has a unique name (string), severity (warning/error), and check function
   - Tests in `tests/test_lint.py`

### Sprint 3: The Market Play
5. MCP intent enforcement (`enforce --mcp`):
   - `src/intentspec/enforce.py` — NEW module
   - Intent-first approach: validate MCP tool capabilities against intent spec
   - Generate intent spec skeleton from MCP server capabilities if no spec exists
   - CLI: `intentspec enforce --mcp <server_url_or_config>`
   - Handles: unreachable servers (warn), servers without specs (flag as risk)
   - Tests in `tests/test_enforce.py`
   - Use stdlib only (no new deps)

## Rules

1. TDD: Write failing test BEFORE implementing each new function
2. One feature per commit, one commit per sprint item
3. No new dependencies — stdlib + existing (click, pyyaml, jsonschema)
4. Type hints on all public functions
5. Use `intentspec.source_resolve` for source file resolution where applicable
6. Performance budgets: validate <100ms, lint <100ms per spec
7. Update PLAN_PHASE2.md with progress markers as you complete each item
8. Run full test suite after each commit: `python3 -m pytest tests/ -q`

## Acceptance Criteria

- [ ] `intentspec migrate` command works on all v1.0 fixtures, produces valid v1.1
- [ ] Converter accuracy benchmark runs and reports current accuracy
- [ ] 15+ lint rules implemented and tested
- [ ] `intentspec enforce --mcp` command works (mock server)
- [ ] All 806+ existing tests still passing
- [ ] New tests added: migrate (10+), lint (20+), enforce (10+)
- [ ] No regressions in existing functionality

## Key Files to Read First

- `src/intentspec/cli.py` — current commands and structure
- `src/intentspec/lint/__init__.py` — current 6 lint rules
- `src/intentspec/source_resolve.py` — source resolution utility
- `tests/benchmark_converter.py` — existing benchmark test
- `tests/fixtures/` — test fixtures corpus
- `intentspec/PLAN_PHASE2.md` — full plan with sprint definitions
- `AGENTS.md` — build profile and conventions

## What NOT to Do

- Do NOT implement framework adapters — already shipped
- Do NOT implement EU AI Act compliance pack — Phase 2B
- Do NOT implement bidirectional agentskills export — Phase 2B
- Do NOT add new dependencies
- Do NOT refactor lint engine to use plugin interface — hardcoded is fine for Phase 2A

## Repository

Working directory: `~/.hermes/profiles/intentspec/workspace/`
Branch: `main`
