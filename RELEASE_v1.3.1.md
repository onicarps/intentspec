## IntentSpec v1.3.1 — QA bugfix release

Patch release fixing packaging and CLI consistency issues found in the independent v1.3.0 QA pass. **977 tests passing.**

### Fixes

- **BUG-1 (CRITICAL):** `init --template` — templates now ship in the wheel (`package-data`)
- **BUG-2 (HIGH):** `gate` — MCP fixtures packaged under `data/mcp/`; no traceback on install
- **BUG-3 (HIGH):** `diff` / `migrate` / `test` — `--format json|yaml` emits parseable output (no header lines)
- **BUG-4 (MEDIUM):** Missing paths return exit **3** on validate, score, coverage, diff, lint, drift, health
- **UX-1:** Coverage shows **N/A** when no source spec (not vacuous 100%)
- **BUG-5:** `analyze` pluralization fix ("1 agent spec")

### Install

```bash
pip install --upgrade intentspec
intentspec --version   # 1.3.1
```

### QA

Independent re-test: **PASS 4/4** — see `INTENTSPEC_V130_RETEST_REPORT.md` in the repo.

### Phase status

Phase 2A + 2B + 2C complete. Phase 3 (beta program) next.