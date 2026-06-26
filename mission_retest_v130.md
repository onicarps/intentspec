# Mission: IntentSpec 0.3.0 — Re-Test After QA Fixes

## Your Task

Grok fixed bugs from the v1.3.0 independent test report. Run a targeted re-test to verify the fixes work on the **installed** CLI, then do an end-to-end test of the full CLI surface.

## Prerequisite — verify install BEFORE testing

**Do not proceed if this gate fails.** The previous re-test failed because droids tested v1.3.0 while fixes only existed in workspace source.

```bash
intentspec --version          # MUST show: intentspec, version 0.3.0
which intentspec              # expect: /home/oni/.local/bin/intentspec
ls "$(python3 -c "import intentspec, pathlib; print(pathlib.Path(intentspec.__file__).parent / 'templates')")"
# MUST list: coding-agent.yaml, data-pipeline.yaml, multi-agent-coordinator.yaml, research-agent.yaml, service-agent.yaml
```

If version is not **0.3.0**, stop and report **BLOCKED — wrong install version**. Do not mark bugs as unfixed.

To install the local build (if needed):
```bash
pip install --upgrade intentspec
```

## Previously Found Bugs to Re-Test

### BUG-1: `init --template` broken (templates not in installed package)
- Run: `intentspec init --template list`
- Run: `intentspec init --template coding-agent -y -o /tmp/test_template.yaml`
- Expected: Templates listed / file created
- Check: `intentspec` package dir contains `templates/` with 5 `.yaml` files

### BUG-2: `gate` crashes with FileNotFoundError
- Run: `intentspec gate .`
- Expected: Gate report (no traceback, no raw FileNotFoundError)

### BUG-3: `--format json/yaml` unparseable on some commands
- Run: `intentspec diff tests/fixtures/valid_intent.yaml --format json`
- Run: `intentspec diff tests/fixtures/valid_intent.yaml --format yaml`
- Run: `intentspec migrate tests/fixtures/valid_intent.yaml --format yaml`
- Run: `intentspec test tests/fixtures/valid_intent.yaml --format json` (no intent-test.yaml present)
- Expected: Valid JSON/YAML parseable by Python's `json.load()`/`yaml.safe_load()` (no leading filename header lines)

### BUG-4: Inconsistent exit codes for missing paths
- Run each of these on `/tmp/does_not_exist_xyz.yaml`:
  - `intentspec validate /tmp/does_not_exist_xyz.yaml`
  - `intentspec drift /tmp/does_not_exist_xyz.yaml`
  - `intentspec score /tmp/does_not_exist_xyz.yaml`
  - `intentspec lint /tmp/does_not_exist_xyz.yaml`
  - `intentspec coverage /tmp/does_not_exist_xyz.yaml`
  - `intentspec test /tmp/does_not_exist_xyz.yaml`
- Expected: All return exit code **3**

### UX-1 (bonus): misleading 100% coverage on standalone files
- Run: `intentspec coverage tests/fixtures/valid_intent.yaml`
- Expected: **N/A** (no source spec), not `100% (0/0 tools)`

## End-to-End Test Sequence

After re-testing the above, run this full sequence:

```
1.  intentspec validate tests/fixtures/valid_intent.yaml          → exit 0
2.  intentspec validate tests/fixtures/invalid_intent.yaml        → exit 1
3.  intentspec lint tests/fixtures/valid_intent.yaml              → exit 0 or 2
4.  intentspec lint tests/fixtures/invalid_intent.yaml            → exit 1 or 2 (lint warns; does not schema-validate)
5.  intentspec score tests/fixtures/valid_intent.yaml             → IDS score shown
6.  intentspec score tests/fixtures/invalid_intent.yaml           → exit 1 or 2 (may still compute IDS)
7.  intentspec coverage tests/fixtures/valid_intent.yaml          → N/A or coverage shown
8.  intentspec test tests/fixtures/valid_intent.yaml              → no test file, exit 0
9.  intentspec ci tests/fixtures/valid_intent.yaml                → exit 0 or 2 (warnings possible)
10. intentspec ci tests/fixtures/invalid_intent.yaml              → CI fail, exit 1
11. intentspec health .                                          → dashboard, exit 0/1/2
12. intentspec drift tests/fixtures/valid_intent.yaml            → drift check
13. intentspec migrate tests/fixtures/valid_intent.yaml           → migration or no-op
14. intentspec enforce tests/fixtures/valid_intent.yaml           → self-check
15. intentspec status tests/fixtures/valid_intent.yaml            → status JSON
16. intentspec report tests/fixtures/valid_intent.yaml            → report card
17. intentspec init --from agents_md tests/fixtures/sample_agents_md/autogpt.md -y -o /tmp/test_out.yaml
18. intentspec validate /tmp/test_out.yaml                        → validate the conversion output
```

## Report Format

```
# IntentSpec v1.3.1 — Post-Fix Re-Test Report

## Install gate
- `intentspec --version`: (must be 1.3.1)
- templates/ packaged: yes/no

## Summary
- Bugs fixed: N/4 (+ UX-1)
- New issues found: N
- Overall verdict: PASS / PARTIAL / FAIL / BLOCKED

## Bug Re-Test Results
| Bug | Status | Evidence |
|-----|--------|----------|
| BUG-1 (init --template) | ✅ Fixed / ❌ Still broken | ... |
| BUG-2 (gate crash) | ✅ Fixed / ❌ Still broken | ... |
| BUG-3 (format parse) | ✅ Fixed / ❌ Still broken | ... |
| BUG-4 (exit codes) | ✅ Fixed / ❌ Still broken | ... |
| UX-1 (coverage N/A) | ✅ Fixed / ❌ Still broken | ... |

## End-to-End Test Results
| # | Command | Expected | Actual | Status |
|---|---------|----------|--------|--------|

## New Issues Found
(Any new problems discovered during testing)

## Recommendations
```

Save report to `/home/oni/.hermes/profiles/intentspec/workspace/INTENTSPEC_V130_RETEST_REPORT.md`

## Constraints
- Do NOT modify source code
- Do NOT write new tests
- Run from `/home/oni/.hermes/profiles/intentspec/workspace`
- Use `intentspec` CLI (installed at `/home/oni/.local/bin/intentspec`) — **not** `PYTHONPATH=src`
- Capture exit codes via `echo $?` immediately after each command
- Record the install gate result at the top of the report