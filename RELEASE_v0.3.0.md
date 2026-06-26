## IntentSpec 0.3.0 — Phase 2 complete (pre-1.0)

Single canonical release for Phase 2A + 2B + 2C. **977 tests passing.**

### What's included

**Phase 2A:** migrate, lint v2 (16 rules), MCP enforce, framework adapters, converter ≥75%

**Phase 2B:** `intentspec test`, `watch`, `init --pre-commit`, `status` + GitHub workflow, `coverage --trend`

**Phase 2C:** `report`, dashboard `/demo`, `analyze`, `gate`, content marketing MVP

**QA fixes** (from independent test pass): templates packaging, gate MCP data, parseable `--format json|yaml`, exit code 3 on missing paths, coverage N/A without source

### Versioning

Pre-1.0 release. Mistaken `1.2.0` / `1.3.0` / `1.3.1` PyPI publishes are yanked. Use **0.3.x** until beta completes and **1.0.0** launches.

### Install

```bash
pip install --upgrade intentspec
intentspec --version   # 0.3.0
```