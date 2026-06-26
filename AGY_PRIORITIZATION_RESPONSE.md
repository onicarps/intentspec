# Agy Prioritization Response — June 26 2026

**Invoked via:** `agy --new-project --print --dangerously-skip-permissions` (heredoc prompt)  
**Brief:** `AGY_PRIORITIZATION_BRIEF.md`

---

## Decision: Hybrid (E → A → D)

## Rationale

The PyPI version is severely stale (0.1.1 vs local 1.2.0), making it critical to ship the current, stable code immediately to gather external signal. Blocking a major release for 1–2 weeks over a 7% coverage delta is anti-growth, so we should bypass the 90% gate for now. Furthermore, aligning with the audit consensus, we must cut low-leverage features like the ONI-200 eval export and pivot our resources to high-leverage growth assets.

## Ordered next 3 tasks

1. **Ops & Scope Cleanup:** Kill all stale factory droids running on shipped work. Update the Phase 2B plan checkboxes to explicitly cut/remove the ONI-200 eval-harness and agentskills export, and add the new growth asset deliverables.
2. **Ship v1.2.0 immediately:** Temporarily lower the CI coverage gate to 80% (or bypass it entirely), push the 6 commits on main, tag the release, and publish v1.2.0 to PyPI.
3. **Initiate Growth Phase:** Assign engineering and marketing resources to begin immediate work on the IntentSpec report card and web demo.