# IntentSpec Resume Point — June 26 2026

## State: Phase 2A + 2B + 2C COMPLETE — Phase 3 NEXT

**Canonical status:** `STATUS.md`

### Release
- **PyPI:** `intentspec==1.3.1` (tag `v1.3.1`, published via GitHub Actions)
- **Tests:** 977 passing, 1 skipped
- **Repo:** github.com/onicarps/intentspec, `main` up to date

### Phase 2B (v1.2.0) — COMPLETE
- `intentspec test` — structural testing (ONI-202)
- `intentspec watch` + `init --pre-commit` (ONI-206)
- `intentspec status` + `.github/workflows/intentspec.yml` (ONI-205)
- `intentspec coverage --trend` (ONI-203)
- ONI-200 eval-harness — **CUT → Phase 3**

### Phase 2C (v1.3.0 → v1.3.1) — COMPLETE
- `intentspec report`, dashboard `/demo`, `intentspec analyze`, `intentspec gate`
- v1.3.1 QA fixes: templates packaging, gate MCP data, parseable `--format`, exit code 3 on missing paths, coverage N/A
- QA: `INTENTSPEC_V130_RETEST_REPORT.md` — PASS 4/4

### To resume work
```bash
cd ~/.hermes/profiles/intentspec/workspace/
pip install --upgrade intentspec   # or: pip install -e ".[dev]" --break-system-packages
intentspec --version               # expect 1.3.1
python3 -m pytest tests/ -q      # expect 977 passed
```

### Phase 3 next (do not re-open 2B/2C)
1. Beta program — recruit 5–10 users on real repos
2. TestPyPI gate before PyPI releases
3. Deferred: ONI-200 eval export, ONI-187 EU AI Act pack, `badge`, agentskills export
4. Growth: real-repo `analyze`, content distribution