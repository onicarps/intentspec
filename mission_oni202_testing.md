# Mission: IntentSpec Phase 2B — Structural Testing Framework (ONI-202)

> **STATUS: SHIPPED** (v1.2.0, June 26 2026). Do not re-implement. See `STATUS.md`.

## Your Task

Implement the structural testing framework for IntentSpec. This is the flagship P0 feature of Phase 2B. The framework evaluates `intent-test.yaml` files against parsed `intent.yaml` dataclasses — pure structural validation with no LLM calls needed.

## Context: What Already Exists (860+ tests passing)

### Source Code
- `src/intentspec/models/intent.py` — `Intent` dataclass with: `version`, `agent_name`, `agent_type`, `agent_description`, `goals`, `constraints`, `non_negotiables`, `tools_allowed`, `tools_denied`, `boundaries`, `escalation`, `failure_modes`, `sub_agents`, `extends`, `metadata`
- `src/intentspec/spec/validate.py` — `validate_file(path) -> (Intent, schema_errors, semantic_warnings)`
- `src/intentspec/lint/__init__.py` — `lint_intent(intent, source_text) -> LintResult` with 16 rules, `LintIssue`/`LintResult` dataclasses
- `src/intentspec/cli.py` — Click group `main` with 14 commands. Exit codes: 0=ok, 1=validation error, 2=warning, 3=fatal. All commands support `--format text|json|yaml`.
- `src/intentspec/enforce.py` — `enforce_mcp(allowed, denied, server_tools) -> EnforcementResult` (pattern for result dataclasses)
- `src/intentspec/score/ids.py` — `compute_ids(intent) -> IdsResult` (pattern for scoring)

### Key Patterns
- Result dataclasses have `to_text()` and `to_dict()` methods
- CLI commands use `@main.command()`, `click.Path()`, `click.Option()`
- TDD: tests in `tests/test_<module>.py` using `tmp_path` fixture
- All YAML parsing uses `yaml.safe_load`

## Phase 2B Tasks

### 10.1: intent-test.yaml Schema + Parser

Create `src/intentspec/test_schema.py`:

```python
"""Schema and parser for intent-test.yaml files."""

@dataclass
class IntentTest:
    name: str
    description: str = ""
    tests: list[TestCase] = field(default_factory=list)

@dataclass
class TestCase:
    name: str
    type: str  # "constraint_check" | "presence_check" | "count_check" | "regex_check" | "cross_reference"
    description: str = ""
    assert: str = ""
    field: str | None = None
    severity: str = "error"  # "error" | "warning"

def parse_intent_test(path: Path) -> IntentTest:
    """Parse intent-test.yaml, validate schema, return IntentTest."""
```

Schema validation rules:
- `type` must be one of the 5 allowed values
- `name` is required
- `assert` is required for constraint_check, count_check, regex_check
- Reject any unknown fields (additionalProperties: false equivalent)

### 10.2: Assertion Engine

Create `src/intentspec/test_engine.py`:

```python
"""Assertion engine for intent tests."""

@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    severity: str
    duration_ms: float

@dataclass
class TestSuiteResult:
    tests: list[TestResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    errors: int = 0
    total_duration_ms: float = 0.0

def run_intent_tests(intent: Intent, intent_test: IntentTest) -> TestSuiteResult:
    """Run all tests against an Intent model."""
```

Assertion types to implement:
- `presence_check` — check if field exists and is non-empty (e.g., `escalation is not null`)
- `count_check` — check collection count (e.g., `len(non_negotiables[severity='hard']) >= 1`)
- `constraint_check` — evaluate simple constraints (e.g., `tools.denied ∩ tools.allowed == ∅`)
- `regex_check` — regex match against string fields
- `cross_reference` — cross-reference between two fields

### 10.3: CLI Command

Add to `src/intentspec/cli.py`:

```python
@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def test(path: str, output_format: str):
    """Run intent tests against intent.yaml."""
```

Behavior:
- Find `intent.yaml` (and optional `intent-test.yaml`) in path
- If no `intent-test.yaml` found, print message and exit 0
- Run tests, output results
- Exit codes: 0=all pass, 1=any failure, 2=warning (skipped tests), 3=missing files

### 10.4: Integration with CI

Update `src/intentspec/ci/__init__.py`:
- In `_evaluate_file()`, if `intent-test.yaml` exists alongside `intent.yaml`, run tests
- Test failures contribute to exit code 1 (validation error)

## Constraints

- **No new dependencies** — stdlib only (use `re` for regex, `yaml` for parsing, `json` for output)
- **TDD** — write `tests/test_test_schema.py` and `tests/test_test_engine.py` first
- **Type hints** on all public functions
- **Google-style docstrings**
- **All code must pass `python3 -m pytest tests/ -q`**
- **Follow existing patterns** — look at `lint/__init__.py` and `enforce.py` for reference
- **Performance budget**: <100ms per intent file
- **Security**: Use `yaml.safe_load` for intent-test.yaml. Never `eval()` or `exec()` assertion strings. Parse assertions into structured checks, not dynamic code execution.

## File Structure to Create

```
src/intentspec/
├── test_schema.py       # IntentTest, TestCase dataclasses + parser
└── test_engine.py       # Assertion engine + TestSuiteResult

tests/
├── test_test_schema.py  # Parser tests (10+)
└── test_test_engine.py  # Engine tests (15+)
```

## Verification

```bash
cd /home/oni/.hermes/profiles/intentspec/workspace
python3 -m pytest tests/test_test_schema.py tests/test_test_engine.py -v
python3 -m pytest tests/ -q  # All existing tests still pass
```

## Phase Gate

- [ ] `intentspec test` command works on intent.yaml + intent-test.yaml
- [ ] All 5 assertion types implemented and tested
- [ ] Exit codes correct (0=pass, 1=fail, 2=warning, 3=missing)
- [ ] JSON/YAML output formats work
- [ ] CI integration picks up test failures
- [ ] No regressions in existing 860+ tests
- [ ] Performance: <100ms per intent file
