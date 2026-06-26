# IntentSpec — Project Status

**Last updated:** June 26 2026

## Current release

| Item | Value |
|------|-------|
| **PyPI version** | `1.3.1` |
| **Git tag** | `v1.3.1` |
| **Tests** | 977 passing, 1 skipped |
| **Repo** | https://github.com/onicarps/intentspec |

## Phase map

| Phase | Version | Status | Shipped |
|-------|---------|--------|---------|
| **2A** — Core moat | v1.1.0 | ✅ **COMPLETE** | migrate, lint v2 (16 rules), MCP enforce, adapters, converter ≥75% |
| **2B** — Inner dev loop | v1.2.0 | ✅ **COMPLETE** | `test`, `watch`, `init --pre-commit`, `status` + GH workflow, `coverage --trend` |
| **2C** — Growth | v1.3.0 → v1.3.1 | ✅ **COMPLETE** | `report`, dashboard `/demo`, `analyze`, `gate`; v1.3.1 QA bugfixes |
| **3** — Publish + integrate | — | 🔜 **NEXT** | TestPyPI gate, beta program (5–10 users), deferred cuts (ONI-200, EU AI Act, badge) |
| **4** — Harden + launch | — | ⏳ Planned | Full adapters, dashboard, drift v2, launch |

## Phase 2B checklist (closed)

- [x] ONI-202 — `intentspec test` structural framework
- [x] ONI-206 — `intentspec watch` + `init --pre-commit`
- [x] ONI-205 — Quiet GitHub status (`status` + `.github/workflows/intentspec.yml`)
- [x] ONI-203 — `intentspec coverage --trend`
- [x] ONI-200 — eval-harness export **CUT → Phase 3**

## Phase 2C checklist (closed)

- [x] Shareable report card (`intentspec report`)
- [x] Web demo (`dashboard --serve` → `/demo`)
- [x] Content marketing MVP (`analyze`, CONTENT_MARKETING_POST.md)
- [x] ONI-195 gate validation report
- [x] v1.3.1 QA fixes (templates packaging, gate data, format output, exit codes, coverage N/A)

## What's next (Phase 3)

1. Beta program — 5–10 users on real repos
2. TestPyPI gate before every PyPI release
3. Deferred scope: eval-harness export (ONI-200), EU AI Act pack (ONI-187), `badge`, agentskills export
4. Growth: expand `analyze` to real public repos, content distribution

## QA artifacts

- Initial QA: `INTENTSPEC_V130_TEST_REPORT.md` (v1.3.0, grade C+)
- Post-fix QA: `INTENTSPEC_V130_RETEST_REPORT.md` (v1.3.1, **PASS 4/4**)

## For droids / agents

**Read this file first.** Do not implement Phase 2A/2B/2C features — they are shipped. New work targets Phase 3 unless explicitly scoped otherwise.