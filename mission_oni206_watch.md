# Mission: IntentSpec Phase 2B — Watch Mode & Pre-commit Hook (ONI-206)

> **STATUS: SHIPPED** (v1.2.0, June 26 2026). Do not re-implement. See `STATUS.md`.

## Your Task

Implement `intentspec watch` and `intentspec init --pre-commit`. These are the inner dev loop utilities — run validate + test on file save, and install a pre-commit hook for automatic checks.

## Context: What Already Exists

### Source Code
- `src/intentspec/cli.py` — Click group with `validate`, `lint`, `test` commands. All support `--format text|json|yaml`
- `src/intentspec/models/intent.py` — `Intent` dataclass
- `src/intentspec/spec/validate.py` — `validate_file(path) -> (Intent, schema_errors, semantic_warnings)`
- `src/intentspec/test_schema.py` — `parse_intent_test(path) -> IntentTest`
- `src/intentspec/test_engine.py` — `run_intent_tests(intent, intent_test) -> TestSuiteResult`
- `src/intentspec/ci/__init__.py` — CI command integration pattern
- Exit codes: 0=success, 1=validation error, 2=warning, 3=fatal

### Patterns to Follow
- `intentspec lint` uses per-line disable comments (# intentspec: disable=rule-name)
- `intentspec ci` aggregates multiple files and computes exit code
- Helper functions in `cli.py` for file discovery: `_find_intent_files()`, `_discover_intent_test()`

## Tasks

### 11.1: `intentspec watch` Command

Add to `src/intentspec/cli.py`:

```python
@main.command()
@click.argument("path", type=click.Path(), default=".")
@click.option("--format", "output_format", ... default="text")
def watch(path: str, output_format: str):
    """Watch for intent.yaml changes and run tests on save."""
```

Behavior:
- Watch `path` for `intent.yaml` file changes (use `watchdog` library or stdlib polling)
- On change: run `validate` + `test` (both commands exist)
- Output: minimal (filename + pass/fail) to stay in terminal
- Exit code: aggregate of validate + test results (0, 1, 2, or 3)
- Ctrl+C to stop

### 11.2: `intentspec init --pre-commit`

Add to `intentspec init` command as an option:

```python
@click.option("--pre-commit", is_flag=True, help="Install pre-commit hook for intentspec")
```

Behavior:
- If flag set: create `.pre-commit-config.yaml` in cwd with intentspec hook
- Hook runs: `intentspec validate && intentspec lint && intentspec test`
- Hook fails on exit code 1 (validation error)
- Hook warns on exit code 2 (lint warning)
- Print message: "Pre-commit hook installed. Add to .gitignore: .intentspec/cache/"

### 11.3: Watch Mode Implementation

Create `src/intentspec/watch.py`:

```python
"""File watching and auto-testing for intent.yaml changes."""

import time
from pathlib import Path
from typing import Callable

def watch_directory(path: Path, callback: Callable[[Path], None]) -> None:
    """Poll path for intent.yaml changes, call callback on change."""
```

Use polling (stdlib only) to avoid new dependencies:
- Poll every 500ms
- Hash file content or check mtime
- If changed: call callback with the file path

### 11.4: Tests

Create `tests/test_watch.py`:
- Test file change detection (create temp file, modify, check callback fires)
- Test pre-commit hook generation (check .pre-commit-config.yaml created correctly)
- Test watch command exit codes

## Constraints

- **No new runtime dependencies** — use stdlib polling (`time.sleep`, `path.stat().st_mtime`)
- **Type hints** on all public functions, Google-style docstrings
- **All code must pass `python3 -m pytest tests/ -q`**
- **Performance:** Poll interval 500ms, latency <100ms after save

## File Structure

```
src/intentspec/
├── watch.py              # New file
├── cli.py                # Extend 'init' and add 'watch' command

tests/
├── test_watch.py           # New file
```

## Verification

```bash
cd /home/oni/.hermes/profiles/intentspec/workspace
# Test watch help
python3 -c "from intentspec.cli import main; from click.testing import CliRunner; r=CliRunner().invoke(main, ['watch', '--help']); print(r.output)"

# Test pre-commit option
python3 -c "from intentspec.cli import main; from click.testing import CliRunner; r=CliRunner().invoke(main, ['init', '--pre-commit', '--help']); print('--pre-commit' in r.output)"
"
# Run tests
python3 -m pytest tests/test_watch.py -v
python3 -m pytest tests/ -q
```

## Phase Gate

- [ ] `intentspec watch` command works
- [ ] `intentspec init --pre-commit` creates valid hook
- [ ] No regressions (940 tests still pass)
- [ ] Exit codes correct (0=pass, 1=error, 2=warning, 3=fatal)