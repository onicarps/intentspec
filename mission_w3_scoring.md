# Mission: IntentSpec Week 3 — Diff, Coverage, Score, Lint Commands

## Your Task
Implement Week 3 of the IntentSpec project: the diff, coverage, score, and lint commands. These are the scoring/analysis layer that operates on the Intent model produced by the converters.

## Context: What Already Exists (225 tests passing)

### Source Code
- `src/intentspec/models/intent.py` — Intent dataclass with all sub-models
- `src/intentspec/spec/schema.py` — Complete JSON Schema v1
- `src/intentspec/spec/validate.py` — Schema + semantic validation
- `src/intentspec/spec/formatter.py` — Terminal output formatter
- `src/intentspec/converter/` — Full converter module (agents_md, skill_md, agentskills, interactive, llm_extract)
- `src/intentspec/cli.py` — Click CLI with validate and init commands working

### IDS Formula (from plan.md)
```
IDS = 100 - (
  tool_coverage    × 0.25 +
  goal_coverage    × 0.15 +
  constraint_cov   × 0.10 +
  non_negot_cov    × 0.15 +
  freshness_score  × 0.10 +
  completeness     × 0.15 +
  consistency      × 0.10
)
```
Positioned as estimate (~73 not 73).

### What You Need to Implement

#### 1. `intentspec diff` command (update existing stub in cli.py)
- Git integration: `git diff` for intent.yaml files
- Show added/removed/changed sections
- `--semantic` flag: intent-level changes (goal X removed, constraint Y relaxed) using Intent model comparison
- Graceful fallback when git unavailable: diff against cached `.intentspec/cache/`
- Handle: shallow clones, detached HEAD, empty repos, monorepos
- `--source-commit` flag: compare from a specific commit
- `--format text|json|yaml` support

#### 2. `intentspec coverage` command (update existing stub in cli.py)
- Structural coverage: count tools mentioned in AGENTS.md/SKILL.md vs tools in `intent.tools.allowed`
- Also count goals, constraints, non-negotiables
- Output: coverage % + missing items list
- Position as "estimate" (~73%)
- `--format text|json|yaml` support
- Per-file and aggregate modes

#### 3. `intentspec score` command (update existing stub in cli.py)
- IDS 0-100 with explicit formula
- `--by-agent` breakdown
- `--weights` flag for custom weighting (JSON string)
- `--format text|json|yaml` support
- Color-coded score (green >80, yellow 50-80, red <50)

#### 4. `intentspec lint` command (update existing stub in cli.py)
- Quality checks (not a full linting engine):
  - goal descriptions > 10 chars
  - constraints have enforceable field
  - tools have rationale
  - non-negotiables have severity
  - no duplicate tool names
  - no empty goals list
  - agent description present and > 10 chars
- `--format text|json|yaml` support

#### 5. Coverage/score output formatter (update formatter.py)
- Per-agent breakdown
- Missing tools list
- Color-coded score
- `--format json|yaml|text`

#### 6. Tests
- Test diff against git repos (use temporary git repos in tests)
- Test coverage calculation
- Test IDS score calculation with known inputs
- Test lint quality checks
- Edge cases: empty files, unicode, missing git, malformed yaml
- Performance: validate < 100ms, diff < 500ms, score < 200ms
- Minimum 20 new tests

## Rules
1. Follow TDD: write each test before its source file
2. Commit after each file with message: "feat(score): <description>" or "feat(diff): <description>" etc.
3. All code must pass: python3 -m pytest tests/ -q
4. All existing 225 tests must still pass
5. No new dependencies beyond stdlib + Click + PyYAML + jsonschema
6. Use yaml.safe_load everywhere
7. Use absolute imports from intentspec
8. Type hints on all functions, Google-style docstrings

## Important Notes
- The CLI already has stubs for diff, coverage, score, and lint commands — replace the stubs
- The Formatter class in spec/formatter.py needs new methods for score and coverage output
- For the diff command, use subprocess to call git, or use gitpython if available (check first)
- For coverage, you need to parse the source AGENTS.md/SKILL.md and count mentioned tools/goals/etc
- The IDS formula components need to be calculated from the Intent model

## Verification
After implementing, run:
```
cd /home/oni/.hermes/profiles/intentspec/workspace
python3 -m pytest tests/ -q
```
All tests (225+ new) must pass.
