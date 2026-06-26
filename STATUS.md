# IntentSpec — Project Status

**Last updated:** June 26 2026

## Versioning policy

IntentSpec is **pre-1.0**. Package version follows **0.x** semver, not phase numbers.

| Package version | Meaning |
|-----------------|---------|
| `0.1.1` | Early alpha (first PyPI publish) |
| **`0.3.0`** | **Current** — Phase 2A + 2B + 2C complete (all QA fixes included) |
| `1.0.0` | Reserved for public launch after beta program |

> **Note:** Tags `v1.2.0` / `v1.3.0` / `v1.3.1` were mistaken phase-aligned publishes (June 26). They are yanked on PyPI. Canonical line is **0.3.x**.

## Current release

| Item | Value |
|------|-------|
| **PyPI version** | `0.3.0` |
| **Git tag** | `v0.3.0` |
| **Tests** | 977 passing, 1 skipped |
| **Repo** | https://github.com/onicarps/intentspec |

## Phase map (delivery phases ≠ package semver)

| Phase | Status | Shipped in 0.3.0 |
|-------|--------|------------------|
| **2A** — Core moat | ✅ **COMPLETE** | migrate, lint v2, MCP enforce, adapters, converter ≥75% |
| **2B** — Inner dev loop | ✅ **COMPLETE** | `test`, `watch`, `init --pre-commit`, `status`, `coverage --trend` |
| **2C** — Growth | ✅ **COMPLETE** | `report`, `/demo`, `analyze`, `gate`, QA/packaging fixes |
| **3** — Publish + integrate | 🔜 **NEXT** | Beta program, TestPyPI gate, deferred cuts |
| **4** — Harden + launch | ⏳ Planned | Full adapters, dashboard, drift v2, **1.0.0 launch** |

## What's next (Phase 3)

1. Beta program — 5–10 users on real repos
2. TestPyPI gate before every PyPI release
3. Deferred: ONI-200, ONI-187 (EU AI Act), `badge`, agentskills export
4. Growth: real-repo `analyze`, content distribution

## QA artifacts

Historical reports used mistaken `1.3.x` version labels during testing:
- `INTENTSPEC_V130_TEST_REPORT.md` — initial QA (issues fixed in 0.3.0)
- `INTENTSPEC_V130_RETEST_REPORT.md` — post-fix PASS 4/4

## Tracking sync

- **Notion / Linear:** synced June 26 2026 — `python3 scripts/sync_phase_status.py`
- **Install gate for QA:** `intentspec --version` must show **0.3.0**

## For droids / agents

**Read this file first.** Phase 2A/2B/2C are shipped in **0.3.0**. New work targets Phase 3 unless explicitly scoped otherwise.