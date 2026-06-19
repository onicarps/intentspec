# Mission: IntentSpec Week 4 — CI/CD Integration

## Your Task
Implement Week 4 of the IntentSpec project: the `ci` command, GitHub Action, GitLab CI template, pre-commit hook, and CI tests. This is the CI/CD integration layer that enables IntentSpec to run in automated pipelines.

## Context: What Already Exists (244 tests passing)

### Source Code
- `src/intentspec/models/intent.py` — Intent dataclass with all sub-models
- `src/intentspec/spec/schema.py` — Complete JSON Schema v1
- `src/intentspec/spec/validate.py` — Schema + semantic validation
- `src/intentspec/spec/formatter.py` — Terminal output formatter
- `src/intentspec/converter/` — Full converter module (agents_md, skill_md, agentskills, interactive, llm_extract)
- `src/intentspec/score/ids.py` — IDS scoring engine (IdsResult, compute_ids)
- `src/intentspec/diff/__init__.py` — Diff module (git integration, semantic diff)
- `src/intentspec/lint/__init__.py` — Lint module (LintIssue, LintResult, lint_intent)
- `src/intentspec/coverage/__init__.py` — Coverage module (CoverageResult, analyze_coverage)
- `src/intentspec/coverage/analyzer.py` — Coverage analyzer
- `src/intentspec/cli.py` — Click CLI with validate, init, diff, coverage, score, lint commands working
- `src/intentspec/templates/` — 3 templates (coding-agent, research-agent, service-agent)

### Test Files
- `tests/test_validate.py` — 28 tests
- `tests/test_converter_*.py` — Converter tests
- `tests/test_score_ids.py` — 19 score tests
- `tests/test_benchmark_converter.py` — 16 benchmark tests
- `tests/test_converter_llm.py` — 6 LLM tests
- `tests/fixtures/valid_intent.yaml` — Valid fixture
- `tests/fixtures/invalid_intent.yaml` — Invalid fixture

### Exit Code Standard (ALL commands)
- `0` = success / pass
- `1` = validation error (schema or semantic)
- `2` = warning (stale, sparse — usable but suboptimal)
- `3` = fatal (missing spec, below threshold, unrecoverable)

### Output Format (ALL commands)
- `--format text` (default) — Human-readable terminal output
- `--format json` — Machine-readable JSON to stdout
- `--format yaml` — YAML to stdout

## Week 4 Tasks

### 4.1: `intentspec ci` command
Create `src/intentspec/ci/__init__.py` with a `run_ci()` function that:
1. Runs validate on the given path(s)
2. Runs lint
3. Runs score
4. Runs coverage
5. Aggregates results and returns a unified exit code:
   - 0 = all pass
   - 1 = any validation error
   - 2 = any warning (stale/sparse)
   - 3 = below threshold (--min-coverage)
6. Supports flags:
   - `--min-coverage N` (default 0) — fail with exit 3 if coverage below N%
   - `--strict` — treat warnings as errors (exit 2 becomes exit 1)
   - `--format json|yaml|text` (default text)
   - `--config PATH` — path to config file
7. Is idempotent and stateless

Wire it into `src/intentspec/cli.py` as the `ci` subcommand.

### 4.2: CI config flags
Ensure all CI flags work correctly:
- `--min-coverage N` — integer 0-100
- `--strict` — boolean flag
- `--format json|yaml|text`
- `--config PATH` — path to intentspec config

### 4.3: GitHub Action
Create `action/action.yml` — a GitHub Action that:
- Runs `intentspec ci` on the repo
- Posts a PR comment with score + coverage results
- Uses `docker://` or `pip install` approach
- Supports `min-coverage` and `strict` inputs

Also create `.github/workflows/intentspec.yml` as an example workflow.

### 4.4: GitLab CI template
Create `.gitlab-ci.yml` — example GitLab CI job that runs `intentspec ci`.

### 4.5: Pre-commit hook
Create `.pre-commit-hooks.yaml` — pre-commit hook config for local validation.
- Staged-only validation
- Fast (only checks changed files)

### 4.6: Generic CI guide
Create `docs/ci-integration.md` — document how to use `intentspec ci` in any CI system (Jenkins, CircleCI, Azure DevOps) using exit codes.

### 4.7: Tests for CI
Create `tests/test_ci.py` with tests for:
- All exit codes (0, 1, 2, 3)
- Flag combinations (--min-coverage, --strict, --format)
- JSON output format
- Idempotency (running twice gives same result)
- Concurrent runs
- Missing file handling
- Multiple file handling

## Constraints
- No new dependencies beyond stdlib + Click + PyYAML + jsonschema
- Type hints on all functions, Google-style docstrings
- All code must pass `python3 -m pytest tests/ -q`
- Follow existing code patterns from score/, lint/, coverage/, diff/ modules
- The ci command should REUSE the existing validate, lint, score, coverage commands — not duplicate logic

## File Structure to Create
```
src/intentspec/ci/
  __init__.py        # run_ci() function
action/
  action.yml         # GitHub Action definition
.github/
  workflows/
    intentspec.yml   # Example GitHub workflow
.gitlab-ci.yml       # GitLab CI example
.pre-commit-hooks.yaml  # Pre-commit hook
docs/
  ci-integration.md  # CI integration guide
tests/
  test_ci.py         # CI command tests
```

## Verification
After implementation, run:
```bash
cd ~/.hermes/profiles/intentspec/workspace
pip install -e ".[dev]" --break-system-packages
python3 -m pytest tests/ -q
intentspec ci tests/fixtures/valid_intent.yaml
intentspec ci tests/fixtures/valid_intent.yaml --format json
intentspec ci tests/fixtures/valid_intent.yaml --min-coverage 50 --strict
echo "Exit code: $?"
```

All tests should pass. The ci command should work with all flag combinations.
