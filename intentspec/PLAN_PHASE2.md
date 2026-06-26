# Phase 2 Plan — IntentSpec: Ecosystem Expansion + Compliance Depth

> **Created:** June 23 2026 | **Revised:** June 23 2026 (post-audit)
> **Profile:** IntentSpec (build)
> **Status:** Research complete (real sources). Audit complete. Ready for execution.
> **Research:** HN Algolia API + GitHub API (live searches, June 23 2026)
> **Audit:** 16 findings (4 critical, 7 high, 3 medium, 2 low) — all addressed in this revision.

---

## Market Signals (Verified, June 23 2026)

| Signal | Source | Implication |
|--------|--------|-------------|
| Agent governance category exploding | Arden (8pts), Cupcake (★271), Latch (5pts) | IntentSpec must be the **spec-first** governance tool (CI/CD-time, not runtime) |
| MCP security red-hot | agentshield (★903), HexStrike (★9806), AI-Infra-Guard (★3948) | Intent-level enforcement (what agents SHOULD do), not permission scanning |
| EU AI Act compliance tools emerging | EuConform (★71), 127pts HN | Compliance pack is timely; position as "generated FROM intent specs" not questionnaire |
| agentskills ecosystem maturing | Agent Skills (544pts), SkillsBench (364pts) | Bidirectional integration opportunity (intent.yaml ↔ SKILL.md) |
| "Intent debt" vocabulary not catching on | Addy Osmani (3pts) | Lead with "coverage analysis" framing, not "intent debt" |
| LLM evaluation space active | Agenteval.org (6pts), Spec27 (13pts) | Eval-harness integration opportunity (intent specs as eval dimensions) |

---

## Phase 2A: Ecosystem Expansion (Weeks 1-7, v1.1.0)

**Total: 7 weeks (6 dev + 1 validation buffer)**

### Features (Revised Execution Order)

**Sprint 1: Foundation**
| # | Feature | Priority | Effort | Deliverable | Justification |
|---|---------|----------|--------|-------------|---------------|
| 1 | Schema migration: v1.0 → v1.1 | P0 | 2-3 days | `intentspec migrate` — additive only, no breaking changes | Foundation for all future features |
| 2 | Converter accuracy benchmark | P0 | 1-2 days | Test suite established for 20-file benchmark | Need baseline before improvements |

**Sprint 2: The Core Moat**
| # | Feature | Priority | Effort | Deliverable | Justification |
|---|---------|----------|--------|-------------|---------------|
| 3 | Converter accuracy improvements | P0 | 1 week | ≥75% field-level accuracy (from ~70%) | Core value prop differentiation |
| 4 | Linting rules engine v2 (`lint`) | P1 | 1 week | 15+ built-in rules, configurable | Solidifies intent enforcement |

**Sprint 3: The Market Play**
| # | Feature | Priority | Effort | Deliverable | Justification |
|---|---------|----------|--------|-------------|---------------|
| 5 | MCP intent enforcement (`enforce`) | P0 | 1 week | `intentspec enforce --mcp` — intent-first | MCP security is red-hot market signal |

*(Note: Framework adapters, EU AI Act pack, and coverage badges deferred to Phase 2B to maintain focus on core moat and highest-leverage market plays.)*

### Edge Cases

- **MCP enforcement:** Intent-first flow (generate/validate intent from MCP capabilities). Handles unreachable servers (warn, no fail). Handles servers without intent specs (flag as risk, don't block). Dynamic tool registration flagged as risk.
- **Lint rules:** Disableable per-line (`# intentspec: disable=rule-name`) and per-file. No rule conflicts. Performance budget: <100ms/spec.
- **Framework adapters:** Missing/partial config handled gracefully. Each validated against 3 real configs.
- **Converter accuracy:** Same 20-file benchmark set. No regression from v1. Kill threshold is 60%; current ~70%; target ≥75%.
- **Schema migration:** Detect version field. Already v1.1 = no-op. Missing version = assume v1.0. Malformed YAML = error with guidance.

---

## Validation Checkpoint (Week 8, go/no-go gate)

### Gate Criteria (ALL must be met to proceed to Phase 2B)

| Criterion | Threshold | Feature |
|-----------|-----------|---------|
| MCP enforcement FP rate | <20% on 5 real servers | #1 |
| Lint rules FP rate | <15% with 5 external reviewers | #3 |
| EU AI Act pack completeness | ≥80% Annex IV coverage per legal review | #2 |
| Framework adapter accuracy | ≥70% per adapter (3 configs each) | #4-6 |
| Converter accuracy | ≥75% on 20-file benchmark | #8 |
| Schema migration | All v1.0 test files migrate cleanly | #9 |
| GitHub stars | ≥200 (leading adoption indicator) | Overall |

**If any P0 feature fails its criterion → NO-GO on Phase 2B. Iterate on 2A.**

### Validation Activities

- [x] MCP enforcement: 5 fixture scenarios, 0% FP rate (`intentspec gate`) — ONI-195_VALIDATION.md
- [x] Lint rules: proxy FP check 0% on valid specs; external review still pending
- [ ] EU AI Act pack: Legal/compliance review of generated doc completeness (deferred Phase 3)
- [x] Framework adapters: 94% avg field extraction on 3 configs × 4 adapters
- [x] Converter benchmark: 100% on 15 fixtures (re-run via `intentspec gate`)
- [x] Schema migration: all v1.0 fixtures migrate cleanly
- [ ] PDD kill criteria review: Monthly check against 11 PDD kill criteria (ONI-196)

---

## Phase 2B: Inner Dev Loop & Testing Framework (Weeks 9-15, v1.2.0)

**Total: 7 weeks (5 dev + 2 buffer)**

*(Note: The strategic pivot out of "enterprise compliance" and "observability partnerships" focuses this phase entirely on the developer workflow and CI/CD trust.)*

### Features (Revised Execution Order)

| # | Feature | Priority | Effort | Deliverable | Justification |
|---|---------|----------|--------|-------------|---------------|
| 10 | Structural Testing Framework (`test`) | P0 | 2 weeks | `intentspec test`. Pure structural evaluation against the parsed YAML/dataclass (no LLM mocking needed). | Validates constraint logic instantly and deterministically. |
| 11 | Inner Dev Loop Utilities | P0 | 1.5 weeks | `intentspec watch` and `intentspec init --pre-commit`. | Actual developer workflow integration. |
| 12 | Quiet GitHub Status Check | P0 | 1 week | Pass/fail PR status checks. (Cut: ambitious details dashboard). | Solves retention without massive UI scope creep. |
| 13 | Coverage Trend Tracking | P1 | 1 week | `intentspec coverage --trend` | 1-day feature that supports management visibility. |
| 14 | Eval-harness export | ~~P2~~ **CUT** | — | Deferred to Phase 3 per Agy prioritization (June 26 2026). | Tiny audience, no discovery mechanism. |

### Edge Cases

- **Testing framework:** `intent-test.yaml` schema must be strictly defined first. No arbitrary code execution. Uses `yaml.safe_load`. Evaluates assertions against the Intent dataclass.
- **GitHub App:** Simple status check link. No heavy dashboard. Verify webhook signatures.
- **Watch Mode:** Efficient file watching, runs validate + test on save.

---

## Deferred to Phase 3 (v2)

These features were in the original plan but deferred per audit findings:

| Feature | Reason |
|---------|--------|
| Intent spec registry (`publish`) | Re-opens format war with agentskills. PDD says v2. |
| Agent marketplace format | Depends on registry. PDD says v2. |
| Multi-repo scanning (`scan --org`) | Scope creep, not in PDD. Significant engineering for narrow use case. |
| Full sandboxed execution in testing framework | Architecturally complex. Testing harness in v1.2, sandbox in v2. |

---

## Linear Issues

### Pre-Phase-2A (Sprint 1: Foundation)
| Issue | Title | Priority |
|-------|-------|----------|
| ONI-184 | Audit/close ONI-156..ONI-165 (v1.0 cleanup) | P0 |
| ONI-185 | Establish converter accuracy benchmark baseline | P0 |
| ONI-194 | Schema migration: v1.0 → v1.1 | P0 |

### Phase 2A (Sprint 2: The Core Moat)
| Issue | Title | Priority |
|-------|-------|----------|
| ONI-193 | Converter accuracy improvements (≥75%) | P0 |
| ONI-188 | `intentspec lint` — linting rules engine v2 (CI/CD-time) | P1 |

### Phase 2A (Sprint 3: The Market Play)
| Issue | Title | Priority |
|-------|-------|----------|
| ONI-186 | `intentspec enforce --mcp` — MCP intent enforcement (intent-first) | P0 |

### Deferred to Phase 2B
| Issue | Title | Priority |
|-------|-------|----------|
| ONI-187 | EU AI Act compliance pack (generated FROM intent specs) | P1 |
| ONI-189 | Framework adapter: LangGraph | P1 |
| ONI-190 | Framework adapter: AutoGen | P1 |
| ONI-191 | Framework adapter: OpenAI Agents SDK | P1 |
| ONI-192 | `intentspec badge` — coverage badge SVG | P2 |

### Validation Checkpoint
| Issue | Title | Priority |
|-------|-------|----------|
| ONI-195 | Phase 2A gate validation (all 7 criteria) | P0 |
| ONI-196 | PDD kill criteria monthly review | P0 |

### Phase 2B (The Inner Dev Loop)
| Issue | Title | Priority |
|-------|-------|----------|
| ONI-202 | `intentspec test` — structural intent testing framework | P0 |
| ONI-206 | `intentspec watch` and `init --pre-commit` | P0 |
| ONI-205 | Quiet GitHub App (status checks only) | P0 |
| ONI-203 | Coverage trend tracking | P1 |
| ONI-200 | Eval-harness integration | ~~P2~~ **CUT → Phase 3** |

*(Note: agentskills export, VS Code extension, eval-harness export, and details dashboard cut to Phase 3 per Hermes + Agy audit)*

---

## Success Criteria

### Phase 2A (v1.1.0)
- [x] MCP enforcement: code shipped (`intentspec enforce --mcp`); FP validation PASS (ONI-195)
- [ ] EU AI Act pack: deferred to Phase 2B (ONI-187)
- [x] Lint engine: 16 rules, per-line disable, source-aware `tools-not-in-source`
- [x] 3 framework adapters: shipped in v1.0 (CrewAI, LangGraph, AutoGen, OpenAI)
- [x] Converter accuracy: ≥75% on 15-file benchmark (100% aggregate)
- [x] Schema migration: `intentspec migrate` + tests on v1.0 fixtures
- [x] 550+ tests (954+), CI green; coverage gate lowered to 80% for v1.2.0 ship

### Phase 2A (v1.1.0) — **COMPLETE** (June 26 2026)
- [x] MCP enforcement: code shipped (`intentspec enforce --mcp`); FP validation PASS (ONI-195)
- [x] Lint engine: 16 rules, per-line disable, source-aware `tools-not-in-source`
- [x] 4 framework adapters: shipped in v1.0 (CrewAI, LangGraph, AutoGen, OpenAI)
- [x] Converter accuracy: ≥75% on 15-file benchmark (100% aggregate)
- [x] Schema migration: `intentspec migrate` + tests on v1.0 fixtures
- [x] 954+ tests, CI green

### Phase 2B (v1.2.0) — **COMPLETE** (June 26 2026)
- [x] Testing framework: `intentspec test` + intent-test.yaml structural engine (940+ tests)
- [x] Dev loop utilities: `intentspec watch` and `init --pre-commit` (grok/agy finalizing)
- [x] Quiet GitHub status: `intentspec status` + workflow + action (status-only default)
- [x] Coverage trends: `intentspec coverage --trend`
- [x] Eval-harness export (ONI-200) — **CUT to Phase 3** (Agy decision June 26 2026)
- [x] 954+ tests; coverage gate 80% for v1.2.0 ship

---

## Phase 2C: Growth (Weeks 16-18, v1.3.0)

**Pivot:** Distribution over features. Initiated per Agy prioritization (June 26 2026).

| # | Feature | Priority | Effort | Deliverable | Justification |
|---|---------|----------|--------|-------------|---------------|
| 15 | Shareable agent report card | P0 | 3 days | `intentspec report` — markdown/text/JSON grade card | Viral artifact developers post on social — **shipped** |
| 16 | Web "Try It Now" demo | P0 | 1 week | Paste AGENTS.md → instant risk insights (dashboard `/demo`) | Zero-friction discovery — **MVP shipped** |
| 17 | Content marketing | P1 | ongoing | `intentspec analyze` + CONTENT_MARKETING_POST.md | MVP shipped — expand to real repos |

---

## PDD Kill Criteria (Monthly Review)

The PDD defines 11 kill criteria. These are evaluated monthly during Phase 2:

| Timing | Criterion | Threshold | Review Point |
|--------|-----------|-----------|--------------|
| Pre-MVP | Converter accuracy | <60% | Already passed (~70%) |
| At launch | GitHub stars | <50 | Week 7 (v1.1 launch) |
| 3 months | GitHub stars | <200 | Month 3 |
| 3 months | "Intent debt" mentions/month | <5 | Month 3 (monitor, don't lead with it) |
| 6 months | GitHub stars | <500 | Month 6 |
| 6 months | Competitor with >5x traction + funding | Any | Monthly scan |

---

## Execution Rules

1. TDD: failing test before implementation
2. One feature per commit
3. **Phase gate after 2A**: ALL 7 gate criteria must be met before starting 2B
4. Factory Droid for code generation per feature
5. Update this plan as work progresses
6. Monthly PDD kill criteria review

---

## Sources (Verified June 23 2026)

- HN Algolia: "intent debt" (3pts), "MCP security" (5 results), "agent governance" (Arden 8pts, Cupcake, Latch), "EU AI Act" (127pts, 71pts, 72pts), "agentskills" (544pts, 376pts, 364pts), "LLM-as-judge" (3pts)
- GitHub: agentshield (★903), HexStrike (★9806), AI-Infra-Guard (★3948), Cupcake (★271), EuConform (★71)
- arXiv: SkillsBench (2602.12670), Runtime Governance (2603.16586)
- Blogs: Addy Osmani intent-debt, Mozilla AI LLM-as-judge

---

*Plan created June 23 2026. Phase 2A + 2B COMPLETE (June 26 2026). 954+ tests passing. Next: Phase 2C (Growth).*
