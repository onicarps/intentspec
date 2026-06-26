# IntentSpec v1.3.1 — Post-Fix Re-Test Report

**Date:** 2026-06-26  
**CLI under test:** `intentspec` (installed) — `intentspec, version 1.3.1`  
**Working directory:** `/home/oni/.hermes/profiles/intentspec/workspace`  
**Scope:** Re-test of 4 bugs from the v1.3.0 independent QA report after v1.3.1 packaging/CLI fixes.

## Install gate

| Check | Result |
|-------|--------|
| `intentspec --version` | **1.3.1** ✅ |
| `templates/` packaged in site-packages | **yes** (5 `.yaml` files) ✅ |
| `data/mcp/` packaged | **yes** ✅ |

> **Note:** An earlier re-test at 19:19 tested **v1.3.0** before the wheel was installed and reported **FAIL (0/4)**. That result is superseded by this report.

## Summary

- **Bugs fixed: 4 / 4** (+ UX-1 coverage N/A)
- **New issues found: 1** (minor UX — `-y` does not skip template name prompt)
- **Overall verdict: PASS**

## Bug Re-Test Results

| Bug | Status | Evidence |
|-----|--------|----------|
| BUG-1 (init --template) | ✅ Fixed | `init --template list` lists all 5 templates. Generation works with `--name` or stdin; output validates clean. |
| BUG-2 (gate crash) | ✅ Fixed | `intentspec gate .` → ONI-195 gate report, exit 0, no traceback. |
| BUG-3 (format parse) | ✅ Fixed | `diff/migrate/test --format json\|yaml` all parseable via `json.load()` / `yaml.safe_load()`. |
| BUG-4 (exit codes) | ✅ Fixed | Missing path on validate/lint/score/coverage/drift/test → exit **3** on all six. |
| UX-1 (coverage N/A) | ✅ Fixed | Standalone file shows `N/A (no source spec found to compare against)`, not vacuous 100%. |

## Detail

### BUG-1 — `init --template`

```
$ intentspec init --template list
Available templates:
  coding-agent, data-pipeline, multi-agent-coordinator, research-agent, service-agent
(exit 0)

$ intentspec init --template coding-agent --name coding-agent -y -o /tmp/test_template.yaml
Wrote /tmp/test_template.yaml (exit 0)

$ intentspec validate /tmp/test_template.yaml
  ✓ /tmp/test_template.yaml: valid (exit 0)
```

**Minor UX (not the original bug):** `-y/--yes` skips interactive review only, not the agent-name prompt. In non-TTY, pass `--name <name>` or pipe stdin.

### BUG-2 — `gate`

Clean markdown report, exit 0, no `FileNotFoundError` traceback.

### BUG-3 — `--format json/yaml`

All four parser checks pass (diff json/yaml, migrate json, test json).

### BUG-4 — exit codes

```
validate: 3  lint: 3  score: 3  coverage: 3  drift: 3  test: 3
```

## Recommendations (post-release)

1. **Publish v1.3.1 to PyPI** so `pip install intentspec` picks up fixes (local install only before publish).
2. **`init --template -y`:** consider skipping name prompt when `-y` is set and default name exists.
3. **Add install-gate to QA missions** — require `intentspec --version` ≥ fix version before bug re-tests.