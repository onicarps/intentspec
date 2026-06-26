# Mission: IntentSpec Phase 2B — Quiet GitHub App (ONI-205)

## Your Task

Implement quiet GitHub App status checks — a passive PR status checker that doesn't require full GitHub App setup. Uses existing GitHub Actions infrastructure.

## Context: What Already Exists

### Source Code
- `action/action.yml` — Existing composite action that posts PR comments
- `src/intentspec/ci/__init__.py` — CI command logic with exit codes
- `src/intentspec/cli.py` — Command patterns, output formats
- `src/intentspec/lint/__init__.py` — Lint rules (16 rules implemented)
- `src/intentspec/test_engine.py` — Structural testing
- Exit codes: 0=success, 1=validation error, 2=warning, 3=fatal

### Existing Action Pattern
The `action/action.yml` already handles PR comments. For ONI-205, we add status checks without the complexity of a webhook-receiving server.

## Tasks

### 12.1: Status Check Command

Add to `src/intentspec/cli.py`:

```python
@main.command()
@click.argument("path", type=click.Path(), default=".")
@click.option("--format", "output_format", ... default="json")  # Default JSON for Actions
def status(path: str, output_format: str):
    """Generate CI status output for GitHub Actions."""
```

Behavior:
- Run validate + lint + test on all intent.yaml in path
- Output JSON with:
  ```json
  {
    "passed": true,
    "issues": [{"file": "...", "severity": "error|warning", "message": "..."}],
    "checks": {"validate": "pass", "lint": "warning", "test": "pass"}
  }
  ```
- Exit code 0 if all pass, 1 if errors, 2 if warnings only, 3 on missing spec

### 12.2: GitHub Action Workflow File

Create `.github/workflows/intentspec.yml`:

```yaml
name: IntentSpec
on: [pull_request]
jobs:
  intentspec:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install intentspec
      - run: intentspec status .
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 12.3: Action Wrapper Update

Update `action/action.yml`:
- Add a new job step or composite action function
- If `--status-only` flag: create a GitHub status check (passed/failed)
- Link to workflow run log (not a separate detail page)
- No PR comments unless `--comment` flag explicitly set

### 12.4: Tests

Create `tests/test_status.py`:
- Test status command on valid intent.yaml (exit 0)
- Test on missing intent.yaml (exit 3)
- Test on lint violations (exit 2)
- Test JSON output structure
- Test GitHub Actions integration format

## Constraints

- **No new runtime dependencies** — stdlib only
- **Type hints** on all public functions, Google-style docstrings
- **All code must pass `python3 -m pytest tests/ -q`**
- **Must work with existing action/action.yml infrastructure**

## File Structure

```
.github/workflows/
└── intentspec.yml           # New file

src/intentspec/
├── cli.py                   # Add 'status' command
├── status.py                # New file (optional, for logic)

action/
└── action.yml               # Extend with --status-only option

tests/
└── test_status.py           # New file
```

## Verification

```bash
cd /home/oni/.hermes/profiles/intentspec/workspace
# Test status command
python3 -c "from intentspec.cli import main; from click.testing import CliRunner; r=CliRunner().invoke(main, ['status', '--help']); print(r.output)"

# Run tests
python3 -m pytest tests/test_status.py -v
python3 -m pytest tests/ -q
```

## Phase Gate

- [ ] `intentspec status` command works
- [ ] GitHub workflow file created
- [ ] Exit codes correct (0, 1, 2, 3)
- [ ] No regressions (tests pass)