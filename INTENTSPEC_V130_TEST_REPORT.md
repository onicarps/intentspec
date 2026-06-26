# IntentSpec v1.3.0 — Independent Test Report

**Tester:** Independent QA pass (no source modified, no tests written, no packages installed)
**Date:** 2026-06-26
**Environment:** Python 3.12.3 · `intentspec` 1.3.0 (installed at `/home/oni/.local/bin/intentspec`)
**Working directory:** `/home/oni/.hermes/profiles/intentspec/workspace`

---

## Summary

- **Commands present in CLI:** 19 (`validate, init, diff, coverage, score, lint, test, ci, audit-report, health, drift, migrate, enforce, watch, status, report, analyze, dashboard, gate`)
- **Commands tested:** 18 functionally + 1 (`dashboard`) help-only (requires `fastapi`/`uvicorn`, not installed — server not started per constraints)
- **Passed (clean):** 9 · **Passed with issues / warnings:** 7 · **Broken:** 2 (`init --template`, `gate`) · **Not testable:** 1 (`dashboard`)
- **Spec/CLI mismatch:** task spec references a `badge` command and `migrate v1.0→v1.1` framing that do not match the actual CLI (no `badge` command exists; CLI adds `analyze`, `dashboard`, `gate`).

### Overall grade: **C+**

The functional core (`validate`, `score`, `lint`, `ci`, `enforce`, `report`, conversion via `init --from`) is solid, fast, and produces good, helpful output. However, **two documented features are completely broken in the installed package** (`init --template`, `gate`), and there are **systemic inconsistencies in exit codes and `--format` output** across commands. These are quality/packaging defects that would bite real users immediately, which caps the grade well below the test count's 954+ tests would suggest.

---

## Per-Command Results

| Command | Status | Issues |
|---------|--------|--------|
| `validate` | ✅ | Exit **1** (not documented **3**) on non-existent path |
| `init --from agents_md/skill_md/agentskills` | ✅ | Works; confidence scoring shown. `agentskills` needs a dir containing `SKILL.md` directly (passing a parent of skill dirs errors) |
| `init --template` | ❌ | **BROKEN** — `list` → "No templates directory found"; `coding-agent` → "unknown template". Templates exist in source but are **not bundled in the installed package** |
| `init --quickstart` | ⚠️ | Interactive; prints the first prompt twice; aborts on empty stdin (not fully testable non-interactively) |
| `diff` | ⚠️ | Text works; **`--format json` and `--format yaml` emit a leading filename header line → output is not parseable JSON/YAML**. Exit 1 (not 3) on missing path |
| `coverage` | ⚠️ | Works, but reports misleading **"100% (0/0 tools)"** on a standalone file that actually declares 3 tools/3 goals (no source spec → vacuous 100%). Exit 1 (not 3) on missing path |
| `score` | ✅ | Clean; `--by-agent`, `--weights` accepted; IDS breakdown matches documented formula |
| `lint` | ✅ | Clean; exit 2 on warnings as documented |
| `test` | ⚠️ | Works; **`--format json` emits plain text** ("No intent-test.yaml found…") → invalid JSON when no test file present. Exit 3 on missing path (inconsistent with validate/lint exit 1) |
| `ci` | ✅ | Correct exit codes (0/1/2/3); `--min-coverage` range-validated (101 → Click error); multi-path supported |
| `audit-report` | ✅ | Generates compliance markdown; exit 0 |
| `health` | ⚠️ | Works; **exit code inconsistent for "0 files" cases**: non-existent path → exit 1, empty dir → exit 0, orphaned spec → exit 2 |
| `drift` | ⚠️ | Works; **exit 0 on a non-existent path (silent success)** — should signal error |
| `migrate` | ⚠️ | Text/JSON work; **`--format yaml` emits markdown-ish text with a `---` header → not valid YAML** |
| `enforce` | ✅ | Works against MCP configs (aligned/gap/denied scenarios); exit 2 on tool mismatch |
| `watch --once` | ✅ | Runs one cycle and exits; JSON output valid |
| `status` | ⚠️ | Works; **defaults to JSON output** while every other command defaults to text (inconsistency) |
| `report` | ✅ | Works; supports extra `markdown` format; report card rendered |
| `analyze` | ⚠️ | Works but **emits two concatenated "Agent Spec Analysis" sections** (declared vs converted) which is confusing; grammar bug "**1 agent specs**"; supports `text/json/markdown` but **not `yaml`** |
| `gate` | ❌ | **CRASHES unconditionally** with an uncaught `FileNotFoundError` traceback (hardcoded path `tests/fixtures/sample_mcp/scenarios.yaml` resolved relative to the installed package dir) |
| `dashboard` | ⬜ | Not tested — requires `fastapi`+`uvicorn` (not installed); starting a server is out of scope |

---

## Bugs Found

### [BUG-1] `init --template` is completely broken in the installed package
- **Severity:** CRITICAL
- **Steps to reproduce:**
  - `intentspec init --template list` → `No templates directory found.`
  - `intentspec init --template coding-agent -y -o /tmp/x.yaml` → `Error: unknown template 'coding-agent'.`
- **Expected:** Lists/creates one of the 5 documented templates (coding-agent, research-agent, service-agent, data-pipeline, multi-agent-coordinator) — these are listed in `init --help` and AGENTS.md as a Phase-1 MVP feature.
- **Actual:** Templates exist in source (`src/intentspec/templates/*.yaml`) but are **absent from the installed package** (`/home/oni/.local/lib/python3.12/site-packages/intentspec/` has no `templates/` dir). This is a packaging defect — template files are not declared as package data, so they are not shipped to pip-installed users.
- **Impact:** A documented core command produces zero working paths for end users.

### [BUG-2] `gate` crashes with an uncaught traceback on every invocation
- **Severity:** HIGH
- **Steps to reproduce:** `intentspec gate .` (or any path)
- **Expected:** A gate validation report (or a graceful error).
- **Actual:** Uncaught `FileNotFoundError: .../python3.12/tests/fixtures/sample_mcp/scenarios.yaml` with a full Python stack trace, exit 1. The code (`gate_validation.py:check_mcp_fp_rate`) reads a hardcoded relative path that resolves against the installed package directory, which never contains test fixtures.
- **Impact:** Command is 100% non-functional for installed users and leaks an internal stack trace (poor UX, looks like a hard crash).

### [BUG-3] `--format json`/`yaml` produce unparseable output on several commands
- **Severity:** HIGH (machine-readability is a stated feature)
- **Cases:**
  - `diff --format json <file>` → leading filename header line before the JSON object → `json.load` fails.
  - `diff --format yaml <file>` → same leading header → invalid YAML.
  - `migrate --format yaml <file>` → emits text with a `--- <file> ---` header → invalid YAML.
  - `test --format json <file>` (no test file) → emits plain text "No intent-test.yaml found…" instead of a JSON object.
- **Expected:** `--format json` always emits a single valid JSON document to stdout; `--format yaml` always emits valid YAML.
- **Actual:** Header/prose lines are interleaved with structured output.
- **Impact:** CI/automation consumers cannot reliably parse these commands' machine output.

### [BUG-4] Inconsistent / incorrect exit codes for non-existent paths
- **Severity:** MEDIUM
- **Steps to reproduce:** run each command on `/tmp/does_not_exist_xyz.yaml`.
- **Observed exit codes:** `validate=1, lint=1, score=1, coverage=1, diff=1, health=1, drift=0, test=3, ci=3, audit-report=3, report=3, status=3, migrate=3, enforce=3`.
- **Expected:** Per the documented contract (3 = fatal: missing spec), all should be **3**.
- **Actual:** Three different exit codes (0, 1, 3) for the same fatal condition. `drift` returning **0** (success) for a missing path is the most dangerous — automation would treat it as "all clear".

### [BUG-5] `analyze` grammar/labeling defects
- **Severity:** LOW
- **Details:** Pluralization "**1 agent specs**" (should be "1 agent spec"); two separate sections both titled "Agent Spec Analysis — Content Marketing Data" are concatenated with differing sample sizes (1 vs 11/12), which reads as contradictory headline statistics.

---

## UX Issues

### [UX-1] `coverage` reports a misleading 100% on standalone files
- A standalone `intent.yaml` with 3 declared tools/goals reports `Tool coverage: 100% (0/0 tools)` / `Goal coverage: 100% (0/0 goals)` because no source spec was found to compare against. Reporting "100%" for a vacuous 0/0 ratio overstates quality. Should display `N/A` or "no source spec found to compare against".
- Related: with a source present, the ratio renders as `100% (4/3 tools)` — a `>1` ratio shown as 100% with a confusing `4/3` label.

### [UX-2] `gate` exposes a raw stack trace instead of a user-facing error
- Even setting aside BUG-2, command errors should be caught and reported with a clean message + appropriate exit code, never a bare traceback.

### [UX-3] `init --quickstart` double-prints the first prompt
- The "What is the agent name? (kebab-case):" prompt is emitted twice before reading input.

### [UX-4] Error messages are generally good
- Positive: `validate` on the invalid fixture gives precise, field-anchored messages with actionable hints (e.g., "allowed values: …", "'severity' is required"). This is a strong point of the tool.

---

## Inconsistencies

### [INC-1] Default output format differs across commands
- `status` defaults to **JSON**; every other command defaults to **text**. Either document this clearly or align defaults.

### [INC-2] `--format` option set is not uniform
- Standard triad is `text|json|yaml`. But: `report` adds `markdown`; `gate` adds `markdown`; `analyze` offers `text|json|markdown` (**no `yaml`**); `dashboard`/`watch`/`status` vary. There is no single consistent format contract across the CLI.

### [INC-3] "No intent.yaml in directory" handled three different ways
- Empty directory: `validate/lint/score/coverage/ci/health/drift` → exit **0** (graceful), but `test/report/status` → exit **3** (fatal). The same condition should map to one exit code class.

### [INC-4] Task-spec vs actual CLI drift
- The task's command list includes `badge` (**no such command exists**) and omits the actual `analyze`, `dashboard`, and `gate` commands. Documentation/spec and the shipped CLI are out of sync.

---

## Performance Issues

Measured wall-clock (includes interpreter + import startup). `import intentspec.cli` alone = **117 ms**.

| Command | Measured (wall) | Documented budget | Verdict |
|---------|-----------------|-------------------|---------|
| `validate` | ~160 ms | < 100 ms | ⚠️ Exceeds wall-clock budget — but ~117 ms is Python/Click import startup; algorithmic time < ~45 ms |
| `lint` | ~150 ms | < 100 ms | ⚠️ Same: startup-dominated |
| `score` | ~150 ms | < 200 ms | ✅ |
| `test` | ~150 ms | < 1 s | ✅ |

### [PERF-1] CLI cold-start overhead dominates per-invocation latency
- **Command:** all
- **Measured:** ~117 ms fixed import cost per invocation
- **Budget:** `validate`/`lint` documented < 100 ms
- **Note:** The processing itself is well within budget; the budgets are effectively unachievable on wall-clock because module import alone exceeds them. Either re-baseline the budgets to exclude startup, or lazy-import heavy modules (jsonschema, yaml, click subcommands) to reduce cold start.

---

## What Works Well (Positives)

- `validate` schema + semantic checks are precise, with helpful, field-anchored hints. Exit 0/1/2 behave as documented.
- `score` IDS breakdown matches the documented formula and freshness decay.
- `ci` aggregation, `--min-coverage` range validation, and multi-path globbing all behave correctly.
- `enforce` (MCP intent enforcement) works across aligned/gap/denied scenarios.
- `init --from` conversions (AGENTS.md, SKILL.md, agentskills) produce annotated output with confidence scores and "fields requiring review".
- JSON/YAML output is valid and well-structured for the majority of commands (`validate, lint, score, coverage, ci, audit-report, health, drift, report, status, enforce`).

---

## Recommendations (priority order)

1. **Fix packaging so `templates/` ships with the wheel** (declare package-data / include in `pyproject.toml`/`MANIFEST.in`). This restores `init --template` (BUG-1). Add a smoke test that runs `init --template list` against the *installed* package, not the source tree.
2. **Fix `gate`'s hardcoded fixture path** (BUG-2): resolve required data relative to packaged data or guard with a clean error; never read repo test fixtures at runtime. Wrap command bodies so no command can emit a raw traceback.
3. **Make `--format json/yaml` output strictly machine-parseable** (BUG-3): remove filename/prose headers from structured output in `diff`, `migrate`, and `test`; always emit a single valid document. Add a CI check that pipes every command's `--format json` through a JSON parser.
4. **Standardize exit codes** (BUG-4, INC-3): one mapping for "path not found" (→ 3) and one for "no intent.yaml in directory" across all commands. `drift` returning 0 on a missing path is the highest-risk case.
5. **Align `--format` contract and defaults** (INC-1, INC-2): document/normalize the format option set and per-command defaults; if `status` intentionally defaults to JSON, state it in help.
6. **Reconsider `coverage` reporting for source-less files** (UX-1): show `N/A`/"no source" instead of a vacuous 100%.
7. **Reconcile the documented command list with the shipped CLI** (INC-4): remove/rename `badge`, document `analyze`/`dashboard`/`gate`.
8. **Re-baseline performance budgets** (PERF-1) to exclude interpreter startup, or lazy-import to cut the ~117 ms cold-start.
9. **Polish:** fix `analyze` pluralization and dual-section labeling (BUG-5); fix `init --quickstart` double prompt (UX-3).

---

## Appendix — Test Methodology

- All commands smoke-tested via `--help`; full command surface enumerated from `intentspec --help`.
- Functional tests run against real fixtures in `tests/fixtures/` (`valid_intent.yaml`, `invalid_intent.yaml`, `sample_agents_md/`, `sample_skills_md/`, `sample_agentskills/`, `sample_mcp/`).
- Edge cases: non-existent path, empty directory, all `--format` variants parsed with Python `json`/`yaml` loaders, range-boundary flags.
- Exit codes captured via `${PIPESTATUS[0]}`; timings via `/usr/bin/time`.
- No source code modified, no tests written, no packages installed.
