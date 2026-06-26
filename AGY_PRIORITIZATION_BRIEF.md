# IntentSpec — Prioritization Brief for Antigravity (Agy)

> **SUPERSEDED** — Historical record from June 26 2026 morning.  
> **Current status:** Phase 2A + 2B + 2C **COMPLETE** · PyPI **v1.3.1** · Phase 3 **next** → see `STATUS.md`

**Date:** June 26 2026  
**From:** Hermes / Grok (code reviewer + implementer)  
**To:** Antigravity (head product manager)  
**Ask:** Pick the next 1–2 moves. Be decisive — we need a clear sequence.

---

## Current State (verified at time of brief — now outdated)

| Item | Status |
|------|--------|
| Version (local) | **1.2.0** *(now 1.3.1 on PyPI)* |
| PyPI published | **0.1.1** *(now 1.3.1)* |
| Git | `main` **6 commits ahead** of `origin/main`, clean tree |
| Tests | **954 passed**, 1 skipped |
| Coverage gate | **83%** vs **90%** target in `pyproject.toml` — **failing** |
| Phase 2A | Shipped locally (migrate, lint v2, enforce) — commit `0a844ec` |
| Phase 2B code | Shipped locally (test, watch, status, coverage trend) — commit `9224d09` |
| ONI-200 eval export | **Not implemented** (no `export` command) |
| ONI-195 FP validation | Pending |
| Stale Factory droids | ONI-206 watch (planning), ONI-202 testing (running), Phase 2A (planning) — all superseded by shipped code |

### Phase 2B audit consensus (PHASE2B_AUDIT.md)
- Testing framework: KEEP (reframe as "agent safety tests")
- Quiet GitHub App / status: KEEP but useful-first
- Eval-harness export: CUT or defer (tiny audience)
- agentskills export: CUT to Phase 3
- ADD: shareable report card, web "try it now", content marketing

---

## Options on the table

### A — Ship v1.2.0 now
Push 6 commits, tag v1.2.0, publish to PyPI/TestPyPI.  
**Pros:** Real artifact, closes Phase 2B loop, enables beta users.  
**Cons:** Coverage gate fails (83% < 90%); ONI-195 not done; eval export missing.

### B — Quality gates first
Raise coverage to 90%, run ONI-195 false-positive validation, then ship.  
**Pros:** Clean release, fewer support issues.  
**Cons:** Delays external signal 1–2 weeks; no user-facing win yet.

### C — ONI-200 eval-harness export
Implement `intentspec export` for eval-harness integration (was P2/deferred).  
**Pros:** Completes plan checkbox; eval-harness profile synergy.  
**Cons:** Audit said CUT — tiny audience, no discovery.

### D — Growth assets (from audit)
Shareable agent report card, web "try it now" demo, content marketing.  
**Pros:** Highest leverage for 0-star project per product audit.  
**Cons:** Not in current Phase 2B code path; new scope.

### E — Ops cleanup
Kill stale Factory droids, update PLAN_PHASE2.md checkboxes, write ONI-200 mission if needed.  
**Pros:** Reduces confusion, aligns tooling with reality.  
**Cons:** No user-visible output.

---

## Constraints

- Solo developer pipeline: Agy (plan) → Hermes/Droids (execute) → Grok (review)
- Factory API available; missions exist but are stale
- User prefers: short messages, structured markdown reports for Agy review
- Phase 2 plan: `workspace/intentspec/PLAN_PHASE2.md`

---

## Question for Agy

Given shipped v1.2.0 code, failing coverage gate, stale PyPI, and audit recommendations to cut eval export and prioritize growth:

1. **What is the single highest-leverage next move?** (Pick A, B, C, D, or E — or a hybrid with explicit ordering)
2. **Ship v1.2.0 with 83% coverage, or block on 90%?**
3. **ONI-200 eval export — implement, defer to Phase 3, or cut?**
4. **Any scope change to Phase 2B plan checkboxes we should commit to now?**

Reply with: **Decision**, **Rationale** (2–3 sentences), **Ordered next 3 tasks** (concrete, assignable).