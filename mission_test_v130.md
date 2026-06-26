# Mission: IntentSpec v1.3.0 — Independent Extensive Testing

## Your Task

Run an independent, extensive test of the complete IntentSpec v1.3.0 CLI tool. You are NOT implementing new code — you are testing what exists and reporting bugs, UX issues, inconsistencies, and quality problems.

## Context

IntentSpec is a Python CLI tool (Click + PyYAML + jsonschema) at v1.3.0 with 954+ tests. It was built over 10 weeks by a solo developer.

### What's Installed
- `intentspec` v1.3.0 (pip install --upgrade intentspec)
- Python 3.12, Click, PyYAML, jsonschema, pytest

### Commands Available
```
intentspec validate [PATH]           # Validate intent.yaml
intentspec init --from AGENTS.md     # Convert AGENTS.md → intent.yaml
intentspec init --from SKILL.md      # Convert SKILL.md → intent.yaml
intentspec init --from agentskills   # Convert agentskills → intent.yaml
intentspec init --template NAME      # From template
intentspec init --quickstart         # Interactive wizard
intentspec diff [--from COMMIT]      # Show intent changes
intentspec coverage [PATH]           # Coverage percentage
intentspec score [--by-agent]        # Intent Debt Score (IDS 0-100)
intentspec lint                      # Quality checks (16 rules)
intentspec test                      # Structural intent tests
intentspec ci [--min-coverage N]     # CI/CD hook
intentspec audit-report [PATH]       # Compliance document
intentspec health                    # Terminal dashboard
intentspec drift                     # Detect stale intents
intentspec migrate                   # Schema migration v1.0→v1.1
intentspec enforce --mcp-config F    # MCP intent enforcement
intentspec watch                     # Watch for changes
intentspec status                    # CI status output
intentspec report                    # Agent report card
intentspec badge                     # Coverage badge SVG
```

### Exit Codes
- 0 = success / pass
- 1 = validation error
- 2 = warning
- 3 = fatal

### Output Formats
- `--format text` (default)
- `--format json`
- `--format yaml`

## Testing Protocol

### Phase 1: Smoke Test Every Command
Run `intentspec <command> --help` for ALL commands. Verify help text is accurate and complete.

### Phase 2: Functional Tests
Run each command with real fixtures in `tests/fixtures/`:
- `validate tests/fixtures/valid_intent.yaml` → exit 0
- `validate tests/fixtures/invalid_intent.yaml` → exit 1
- `lint tests/fixtures/valid_intent.yaml` → exit 0 or 2
- `score tests/fixtures/valid_intent.yaml` → shows IDS score
- `coverage tests/fixtures/valid_intent.yaml` → shows coverage
- `test tests/fixtures/valid_intent.yaml` → no test file → exit 0
- `ci tests/fixtures/valid_intent.yaml` → CI pass
- `health` → dashboard output
- `drift tests/fixtures/valid_intent.yaml` → drift check
- `report tests/fixtures/valid_intent.yaml` → report card
- `badge tests/fixtures/valid_intent.yaml` → SVG output

### Phase 3: Edge Cases
- Run each command on a non-existent path → should exit 3
- Run each command on a directory with no intent.yaml → graceful message
- Run with `--format json` on all commands → valid JSON
- Run with `--format yaml` on all commands → valid YAML
- Run `init --from AGENTS.md` on `tests/fixtures/sample_agents_md/complex.md`
- Run `init --from SKILL.md` on `tests/fixtures/sample_skills_md/complex.md`
- Run `init --from agentskills` on `tests/fixtures/sample_agentskills/`
- Run `init --template coding-agent` → creates file
- Run `init --quickstart` → interactive (skip if non-interactive)
- Run `migrate` on a v1.0 fixture → migration output
- Run `enforce` without --mcp-config → self-check behavior
- Run `enforce --mcp-config` on a test MCP config

### Phase 4: Output Quality
- Are error messages helpful? Do they tell you HOW to fix?
- Are exit codes consistent? (0=ok, 1=validation, 2=warning, 3=fatal)
- Is JSON output valid and parseable?
- Is YAML output valid?
- Is text output readable (not too wide, proper alignment)?
- Do `--help` descriptions match actual behavior?

### Phase 5: Consistency
- Do all commands support `--format text|json|yaml`?
- Do all commands return appropriate exit codes?
- Are flag names consistent across commands?
- Is the `init` subcommand UX coherent?

### Phase 6: Performance
- `validate` should be <100ms per file
- `lint` should be <100ms per file
- `score` should be <200ms per file
- `test` should be <1s for small suites

## Report Format

Produce a structured report:

```
# IntentSpec v1.3.0 — Independent Test Report

## Summary
- Total commands tested: N
- Passed: N | Failed: N | Warnings: N
- Overall grade: A/B/C/D/F

## Per-Command Results
| Command | Status | Issues |
|---------|--------|--------|
| validate | ✅/⚠️/❌ | ... |

## Bugs Found
### [BUG-1] Title
- Severity: CRITICAL/HIGH/MEDIUM/LOW
- Steps to reproduce:
- Expected:
- Actual:

## UX Issues
### [UX-1] Title
- Description:

## Inconsistencies
### [INC-1] Title
- Description:

## Performance Issues
### [PERF-1] Title
- Command: X
- Measured: Yms
- Budget: Zms

## Recommendations
1. ...
2. ...
```

## Constraints
- Do NOT modify any source code
- Do NOT write new tests
- Do NOT install new packages
- Run from `/home/oni/.hermes/profiles/intentspec/workspace`
- Use `intentspec` CLI (not python -m pytest)
- Time each command with `time` if possible
- Save the report to `/home/oni/.hermes/profiles/intentspec/workspace/INTENTSPEC_V130_TEST_REPORT.md`
