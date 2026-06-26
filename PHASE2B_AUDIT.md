# Phase 2B Audit Report — IntentSpec v1.2.0

> **Date:** June 26 2026
> **Auditors:** 3 expert subagents (Software Architect, Product Manager, Security/Infrastructure)
> **Scope:** Phase 2B plan at `intentspec/PLAN_PHASE2.md`
> **Context:** 860+ tests passing, 0 GitHub stars, solo developer

---

## Executive Summary

| Auditor | Score | Core Message |
|---------|-------|-------------|
| Product Manager | 5.5/10 | Good engineering, weak growth. Need distribution, not features. |
| Security/Infra | 6/10 | Well-scoped, but testing framework schema must be defined first. |
| Software Architect | 6.5/10 | Feasible with cuts. Add watch mode + pre-commit. Cut detail page. |

**Consensus:** Phase 2B is feasible but needs restructuring. Testing framework is the right P0. The "Quiet GitHub App" detail page is a hidden 3-week project. Eval-harness and agentskills export should be cut or deprioritized.

---

## 1. Product Audit (5.5/10)

### Developer Pain Point Validation

**"Testing agent constraints locally"** — Real pain, but wrong framing. Developers don't wake up wanting "sub-second mocking." They wake up wanting confidence their agent won't misbehave.

**Quiet GitHub App** — Solves IntentSpec's retention problem, not the developer's problem. The conversion funnel (sees status check → clicks Details → installs CLI → writes intent.yaml) has ~0.2% conversion rate. Passive = invisible.

**Eval-harness integration** — Solution-looking-for-problem. Built for ~100 developers, not 10,000. Tiny audience, no organic discovery.

**agentskills export** — Clever but premature. Retention tool disguised as acquisition. Reduces lock-in, which paradoxically increases adoption by reducing risk.

### Top 3 Things That Move Needle (0-star project)

1. **Shareable artifact** — Agent report card, beautiful CLI output that developers post on social media
2. **"Try it now" web experience** — Zero-friction: paste AGENTS.md → get risk insights. No pip install.
3. **Content marketing with real data** — "We analyzed 50 agent projects. 73% have no constraints." Gets linked, cited, shared.

### Recommended Scope Changes

| Current Feature | Recommendation | Rationale |
|----------------|----------------|-----------|
| Intent testing framework | **KEEP** but reframe as "agent safety tests" | Real pain, wrong framing |
| Quiet GitHub App | **KEEP** but useful-first, marketing-second | Current plan too passive |
| Eval-harness integration | **CUT** | Tiny audience, no discovery mechanism |
| agentskills export | **CUT to Phase 3** | Non-target audience |
| — | **ADD: Web "Try It Now" demo** | Highest leverage for 0-star project |
| — | **ADD: Shareable agent report card** | Viral potential |
| — | **ADD: Content marketing (analyze real specs)** | Drives organic discovery |

---

## 2. Security Audit (6/10)

### Per-Feature Risk Assessment

| Feature | Risk Level | Top Concern |
|---------|-----------|-------------|
| Testing Framework | **HIGH** | Malicious `intent-test.yaml` → RCE if schema undefined |
| Quiet GitHub App | **MEDIUM-HIGH** | Webhook auth / token storage (if server component) |
| Eval-harness | **MEDIUM** | Sensitive data leakage via export |
| agentskills export | **MEDIUM** | Internal logic exposure in SKILL.md |
| Supply Chain | **LOW** | Current 3 deps are minimal and well-maintained |

### Critical Recommendations

1. **Define `intent-test.yaml` schema FIRST** — before writing any code. Must NOT allow: arbitrary code, `!` YAML tags, path traversal, import/include directives.

2. **Use `yaml.safe_load` everywhere** in test framework. Never `yaml.load` with default Loader.

3. **Add `--redact` / `--public` mode** to agentskills export. Strip `rationale`, `failure_modes`, `escalation` for public sharing.

4. **No new runtime dependencies** — use `unittest.mock` (stdlib), `urllib.request` (stdlib), `string.Template` (stdlib).

5. **Define `intentspec test` exit codes** — recommend: 0=pass, 1=test failure, 2=test error, 3=fatal.

6. **Webhook signature verification** — if any server component, implement `X-Hub-Signature-256` HMAC. If purely GitHub Actions composite, document this explicitly.

7. **CI timeout enforcement** — hard timeout of 30s for `intentspec test` in CI.

---

## 3. Architecture Audit (6.5/10)

### Per-Feature Feasibility

| Feature | Score | Realistic Estimate | Key Risk |
|---------|-------|-------------------|----------|
| Testing framework | 8/10 | 2 weeks | Scope creep if adding "behavioral" tests |
| Quiet GitHub App | 5/10 | 2.5 weeks | Detail page is a hidden 3-week project |
| Eval-harness | 7/10 | 0.5 week | Format coupling with moving target |
| agentskills export | 6/10 | 0.5 week | Low strategic value |

### What's Missing from "Inner Dev Loop"

1. **`intentspec watch`** — file watcher that runs validate + test on save. Should be P0, 3 days.
2. **`intentspec test --snapshot`** — snapshot testing for intent drift detection.
3. **Pre-commit hook integration** — `intentspec init --pre-commit`. 1-day feature that drives adoption.
4. **`intentspec explain <rule>`** — when test fails, explain WHY and how to fix.
5. **IDE diagnostics** — minimal LSP or `validate --watch` mode.

### Timeline Reality Check

| Feature | Plan | Realistic | Notes |
|---------|------|-----------|-------|
| Testing framework | 2 weeks | 2 weeks | Well-scoped |
| Quiet GitHub App | 1.5 weeks | 2.5 weeks | Detail page underestimated |
| Eval-harness | 1 week | 0.5 week | Simple export |
| agentskills export | 1 week | 0.5 week | Simple template |
| Buffer | 2 weeks | 1 week | |
| **Total** | **7 weeks** | **6.5-7 weeks** | Tight but possible with cuts |

### Recommended Phase 2B Pivot

**Cut:**
- agentskills export → Phase 3
- Eval-harness detail page → Phase 3
- "Beautiful detail page" → simple status check link

**Add:**
- `intentspec watch` (3 days)
- `intentspec init --pre-commit` (1 day)
- `intentspec coverage --trend` (1 day) — killed unjustly

**Revised Timeline:**

| Sprint | Feature | Effort |
|--------|---------|--------|
| 1 | Testing framework (`test`) | 2 weeks |
| 2 | Status checks + `watch` + pre-commit | 1.5 weeks |
| 3 | Coverage trend + eval export + buffer | 1.5 weeks |
| Buffer | Integration testing, edge cases | 2 weeks |

---

## 4. Killed Features — Justification Review

| Killed Feature | Justification | Assessment |
|----------------|--------------|------------|
| VS Code extension | Scope creep, maintenance burden | ✅ **Correct kill.** |
| Behavioral drift detection v2 | Not in PDD | ⚠️ **Questionable.** Git-based drift in 2A is useful; v2 comparing intent vs actual agent behavior is harder but more valuable. |
| SOC 2 audit pack | Strategic pivot away from enterprise | ✅ **Correct kill.** |
| Team dashboard | Not in PDD | ✅ **Correct kill.** |
| Coverage trend tracking | Not in PDD | ⚠️ **Should be kept.** 1-day feature, directly supports inner dev loop. |

---

## 5. Consolidated Recommendations

### Must Do

1. **Testing framework** (P0, 2 weeks) — define schema first, then build
2. **`intentspec watch` + pre-commit** (P0, 1 week) — actual inner dev loop
3. **Status checks** (P0, 1 week) — passive distribution mechanism

### Should Do

4. **Coverage trend** (1 day) — killed unjustly
5. **Eval-harness export** (2-3 days) — simple `--format` flag

### Cut to Phase 3

- agentskills export
- Beautiful detail page
- VS Code extension (already killed)

### Security Must-Haves

- `intent-test.yaml` schema validation before any code
- `yaml.safe_load` everywhere
- `--redact` mode for exports
- No new runtime dependencies
- Exit code definitions for `intentspec test`

---

## 6. intent-test.yaml Proposed Schema

```yaml
version: "1.0"
agent: my-agent
tests:
  - name: "denied-tools-not-in-allowed"
    type: constraint_check
    description: "Denied tools must not appear in allowed list"
    assert: "tools.denied ∩ tools.allowed == ∅"

  - name: "hard-non-negotiables-exist"
    type: presence_check
    description: "At least one hard non-negotiable must be defined"
    assert: "len(non_negotiables[severity='hard']) >= 1"

  - name: "escalation-defined"
    type: presence_check
    assert: "escalation is not null"

  - name: "all-goals-have-success-criteria"
    type: constraint_check
    assert: "all(goals, g => g.success_criteria.length > 0)"

  - name: "enforceable-constraints-have-keywords"
    type: constraint_check
    assert: "all(constraints[c.enforceable], c => has_checkable_keywords(c.rule))"
```

**Assertion types needed:** `constraint_check`, `presence_check`, `count_check`, `regex_check`, `cross_reference`

**Key insight:** No mocking needed. This is pure structural evaluation against the Intent dataclass. The "mocking" is that the framework operates on parsed YAML, not live agent execution.

---

## 7. Exit Code Contract

| Code | Meaning | `intentspec test` |
|------|---------|-------------------|
| 0 | Success / pass | All tests pass |
| 1 | Validation error | Test failure |
| 2 | Warning | Test error (infra issue) |
| 3 | Fatal | Missing test file, schema invalid |

---

*Report generated June 26 2026. Review implementation files at `src/intentspec/`.*
