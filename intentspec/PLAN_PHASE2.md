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

- [ ] MCP enforcement: 5 real servers, measure FP rate, document edge cases
- [ ] Lint rules: 5 external developers review, measure FP rate, target <15%
- [ ] EU AI Act pack: Legal/compliance review of generated doc completeness
- [ ] Framework adapters: 3 real configs per adapter, measure extraction accuracy
- [ ] Converter benchmark: Re-run 20-file benchmark
- [ ] Schema migration: Test against all v1.0 fixture files
- [ ] PDD kill criteria review: Monthly check against 11 PDD kill criteria

---

## Phase 2B: Compliance Depth + Drift Detection (Weeks 9-18, v1.2.0)

**Total: 10 weeks (8 dev + 2 buffer for external dependencies)**

### Features (in execution order)

| # | Feature | Priority | Effort | Deliverable | Market Signal |
|---|---------|----------|--------|-------------|---------------|
| 10 | VS Code extension (basic) | P1 | 2 weeks | Inline validation, coverage display, intent.yaml autocomplete. Early DX investment drives adoption. | PDD adoption playbook: Month 4 target |
| 11 | Behavioral drift detection v2 (`drift`) | P1 | 2 weeks | `intentspec detect-drift` — compare agent behavior logs against intent spec. Configurable sensitivity. Extends v1 `drift` command. | PDD standout feature; was in v1 Phase 4; completely missing from original Phase 2 plan |
| 12 | SOC 2 audit pack | P0 | 1 week | `intentspec compliance soc2` — SOC 2 Type II artifacts. Versioned, timestamped. | Enterprise compliance need |
| 13 | Eval-harness integration | P1 | 1 week | Output intent specs as eval dimensions for eval-harness. `intentspec export --format eval-harness`. | PDD: "intent specs as eval dimensions"; SkillsBench 364pts; agenteval.org 6pts |
| 14 | Team dashboard (extends v1) | P0 | 2 weeks | Extend v1 `dashboard --serve` with multi-agent aggregate IDS, team-level coverage, trend charts. Handles 100+ agents. | Enterprise need |
| 15 | Intent testing framework (`test`) | P0 | 3 weeks | `intentspec test` with `intent-test.yaml` format. Testing harness (not full sandboxed execution in v1.2). Timeout handling. | SkillsBench, agenteval.org |
| 16 | Coverage trend tracking | P1 | 3-4 days | `intentspec coverage --trend` — coverage over time per agent | Management reporting |
| 17 | Bidirectional agentskills integration | P1 | 1 week | `intentspec export --to-skill-md` — intent.yaml → SKILL.md. Complements existing SKILL.md → intent.yaml converter. | Market signal: agentskills ecosystem maturing; PDD complement positioning |

### Edge Cases

- **Drift detection:** Non-deterministic agents (statistical approach, configurable sensitivity: strict/moderate/lenient). Missing logs (warn). Time window (7d/30d/90d).
- **Testing framework:** Timeout (30s default). Test fixtures. Deterministic test runs. Fuzzy matching for non-deterministic responses. Scope: testing harness, not full sandbox (sandbox → v2).
- **Team dashboard:** Extends existing v1 FastAPI dashboard (not a separate product). Pagination + caching for 100+ agents.
- **Eval-harness integration:** Graceful degradation when eval-harness not installed. Documented integration path.
- **agentskills export:** Handles intent.yaml features with no SKILL.md equivalent (documented mapping gaps).

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

### Phase 2B
| Issue | Title | Priority |
|-------|-------|----------|
| ONI-197 | VS Code extension (basic) — inline validation + coverage | P1 |
| ONI-198 | `intentspec detect-drift` — behavioral drift detection v2 | P1 |
| ONI-199 | SOC 2 audit pack | P0 |
| ONI-200 | Eval-harness integration (intent specs as eval dimensions) | P1 |
| ONI-201 | Team dashboard (extends v1, multi-agent aggregate) | P0 |
| ONI-202 | `intentspec test` — intent testing framework | P0 |
| ONI-203 | Coverage trend tracking | P1 |
| ONI-204 | Bidirectional agentskills integration (export to SKILL.md) | P1 |

---

## Success Criteria

### Phase 2A (v1.1.0)
- [ ] MCP enforcement: <20% FP rate on 5 real servers, intent-first positioning clear
- [ ] EU AI Act pack: ≥80% Annex IV coverage per legal review
- [ ] Lint engine: 15+ rules, <15% FP rate with 5 external devs
- [ ] 3 framework adapters: ≥70% accuracy each on 3 real configs
- [ ] Converter accuracy: ≥75% on 20-file benchmark
- [ ] Schema migration: all v1.0 files migrate cleanly
- [ ] 550+ tests, 88%+ coverage, CI green

### Phase 2B (v1.2.0)
- [ ] VS Code extension: inline validation + coverage display
- [ ] Drift detection: flags stale intents, configurable sensitivity
- [ ] SOC 2 pack: generates Type II artifacts
- [ ] Eval-harness integration: exports intent specs as eval dimensions
- [ ] Team dashboard: handles 100+ agents, extends v1
- [ ] Testing framework: intent-test.yaml format, timeout handling
- [ ] Coverage trends: tracks over time per agent
- [ ] agentskills export: intent.yaml → SKILL.md
- [ ] 650+ tests, 88%+ coverage

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

*Plan created June 23 2026. Research complete. Audit complete (16 findings, all addressed). Revised: added drift detection, eval-harness integration, agentskills export, schema migration, gate criteria. Deferred registry/marketplace/multi-repo to v3. Extended Phase 2B to 10 weeks. Downgraded converter accuracy to P1, badges to P2. Ready for build agent execution.*
