# Implementation Plan — IntentSpec v2

**Created:** June 17 2026
**PDD Reference:** `research/intentspec/product-decision-doc.md` (v14)
**Audit Input:** Subagent audit (47 findings, June 17 2026)
**Timeline:** 10 weeks (solo developer)
**Stack:** Python, Click (CLI), PyYAML, jsonschema, pytest

---

## Changes from v1 Plan

Based on the audit, these are the key structural changes:

1. **Schema expanded to match BEST-PRACTICES research** — enforceable bool, rationale on tools, severity on non-negotiables, success_criteria, failure_modes, status lifecycle, boundaries, escalation
2. **agentskills added as first-class input format** — `init --from agentskills` in Phase 1, not deferred
3. **Interactive converter with confidence scores** — no more fire-and-forget 60% accuracy
4. **CrewAI adapter moved to Phase 2** — one framework adapter ships with MVP, not week 8
5. **TestPyPI gate added before PyPI publish** — no direct publish without validation
6. **Beta program added before launch** — 5-10 external users before HN
7. **W10 is all buffer** — blog/HN prep moved to W9
8. **Cross-cutting concerns added** — config file, exit code standard, output format standard, lock file, security audit
9. **IDS metrics explicitly defined** — freshness, completeness, consistency all have formulas
10. **Semantic validation layer** — beyond jsonschema structural checks

---

## intent.yaml v1 Schema (REVISED)

From BEST-PRACTICES.md §3 + FEASIBILITY.md §2 + audit findings:

```yaml
# intent.yaml v1.0

# *Format version (required)
version: "1.0"

# *Agent identity (required)
agent:
  name: string                    # Required. kebab-case identifier.
  type: enum                       # Required. coding | research | service | data | coordinator | custom
  description: string              # Required. ≤200 chars.

# *Intent specification (required)
intent:
  goals:                           # Optional.
    - description: string          # Required. What the agent achieves.
      priority: enum               # high | medium | low
      success_criteria: string     # Optional. How to measure this goal.

  constraints:                     # Optional.
    - rule: string                 # Required. The rule text.
      enforceable: boolean         # Required. true = auto-checkable, false = human judgment.

  non_negotiables:                 # Optional. Hard boundaries.
    - rule: string                 # Required.
      severity: enum               # hard = CI fail, soft = CI warning.

  tools:                           # Optional.
    allowed:                       # Tools the agent CAN use.
      - name: string               # Required.
        rationale: string          # Required. WHY this tool is needed.
    denied:                        # Tools the agent CANNOT use.
      - name: string               # Required.
        rationale: string          # Required. WHY this tool is forbidden.

  boundaries:                      # Optional.
    - scope: string                # What's in scope.
      out_of_scope: string         # What's explicitly out.

  escalation:                      # Optional.
    trigger: string                # When to escalate.
    method: string                 # How (human review, supervisor agent, etc.).

  failure_modes:                   # Optional. Known ways this agent can fail.
    - mode: string                 # Required.
      mitigation: string           # Required.

  # Reserved for future use (Phase 4 adapters):
  sub_agents: [string]             # Optional. Child agent names.
  extends: string                  # Optional. Path to parent intent.yaml.

# Provenance & lifecycle
metadata:                          # Optional.
  status: enum                     # draft | active | deprecated
  owner: string                    # Team/person accountable.
  created: ISO-8601
  updated: ISO-8601
  review_cycle: enum               # weekly | monthly | quarterly
  tags: [string]

# Extension point: Domain-specific blocks (ignored by core validator)
# Examples: hipaa:, soc2:, gdpr:
```

### Schema Design Principles
- **Minimal core:** 5 required fields (version, agent.name, agent.type, agent.description, intent)
- **Additive evolution:** v1 fields never removed or renamed
- **enforceable boolean:** THE key design decision — splits automatable vs human-judged constraints
- **rationale on tools:** Every tool permission has a *why*
- **severity on non-negotiables:** hard = CI fail, soft = CI warning
- **failure_modes first-class:** Most specs only document what should happen
- **status lifecycle:** draft -> active -> deprecated (from DESIGN.md FSM)

---

## IDS Formula (REVISED — Explicitly Defined)

```
IDS = 100 - (
  tool_coverage    × 0.25 +
  goal_coverage    × 0.15 +
  constraint_cov   × 0.10 +
  non_negot_cov    × 0.15 +
  freshness_score  × 0.10 +
  completeness     × 0.15 +
  consistency      × 0.10
)
```

| Component | Weight | Definition |
|-----------|--------|------------|
| **tool_coverage** | 25% | `tools.allowed` count / tools detected in AGENTS.md or framework config |
| **goal_coverage** | 15% | `intent.goals` count / goals detected in AGENTS.md or framework config |
| **constraint_cov** | 10% | `intent.constraints` with `enforceable: true` / total constraints |
| **non_negot_cov** | 15% | `intent.non_negotiables` with `severity: hard` / total non-negotiables |
| **freshness** | 10% | `e^(-0.693 * days_since_update / 30)` — 30-day half-life. Based on file mtime vs now |
| **completeness** | 15% | Weighted ratio of populated optional fields to total optional fields |
| **consistency** | 10% | 100% if no conflicts (tools.denied vs tools.allowed overlap, non_negotiables contradicting goals), 0% if conflicts exist |

**Positioning:** IDS is an *estimate*, not a measurement. Display as `~73` not `73`.

---

## Exit Code Standard (All Commands)

| Code | Meaning |
|------|---------|
| 0 | Success / pass |
| 1 | Validation error (schema or semantic) |
| 2 | Warning (usable but suboptimal — e.g., sparse spec, stale intent) |
| 3 | Fatal (missing spec, below threshold, unrecoverable error) |

---

## Output Format Standard (All Commands)

Every command supports `--format <mode>`:

| Mode | Use |
|------|-----|
| `text` (default) | Human-readable terminal output with colors |
| `json` | Machine-readable JSON to stdout |
| `yaml` | YAML to stdout |

---

## Phase 1: Core CLI + Spec Format (Weeks 1-3)

### Week 1: Project Scaffold + Schema + Validation

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 1.1 | `pyproject.toml` | Package: `intentspec`, entry point: `intentspec`, deps: click>=8.0,<9.0, pyyaml>=6.0,<7.0, jsonschema>=4.0,<5.0. Generate lock file via `pip-compile`. | 1 |
| 1.2 | Directory structure | `src/intentspec/{cli,spec,converter,coverage,score,ci,models}/` + `tests/fixtures/` | 0.5 |
| 1.3 | `Intent` model class | Python dataclass that parses + validates intent.yaml. All commands operate on this model, not raw YAML. Schema version registry (maps version -> validation rules). | 3 |
| 1.4 | `intent.yaml` v1 JSON Schema | Full schema from § above. `additionalProperties: false` on all objects. Draft-07. | 2 |
| 1.5 | Semantic validation layer | Beyond jsonschema: non-empty goals check, unique tool names, no denied-allowed overlap, non_negotiables not subset of constraints, field name typo detection. | 2 |
| 1.6 | `intentspec validate` command | Glob for `intent.yaml`, validate against schema + semantic checks, report errors with file:line:col. `--strict` flag (warn on unknown fields). `--format` support. | 2 |
| 1.7 | Error output formatter | Colored terminal output, file:line:col, suggestion hints (e.g., "did you mean 'constraints'?"). Handles Unicode, BOM, encoding errors. | 1.5 |
| 1.8 | `.intentspec.yaml` config | Optional config file in project root. Supports: default_format, strict_mode, min_coverage. Precedence: CLI flags > env vars > config > defaults. | 1 |
| 1.9 | Tests: validate + schema | 20+ tests: valid schema, missing fields, wrong types, malformed YAML, Unicode, BOM, encoding, semantic errors, unknown fields, config file loading. | 3 |

**Week 1 gate:** `intentspec validate` works on 10+ sample files. Schema validates correctly. Semantic checks catch real errors. Config file works. Tests pass.

### Week 2: Converter (AGENTS.md + SKILL.md + agentskills)

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 2.1 | AGENTS.md parser | Extract sections via regex + heuristics. Handle: empty files (error + helpful message), no agent definition (interactive prompt), multiple agents (extract first + warning), non-English (attempt + flag), recursive references (follow up to 2 levels). | 3 |
| 2.2 | Rule-based extraction | NEVER/MUST/ALWAYS -> constraints (enforceable: true). Code blocks -> tools. Section headers -> goals. Pattern density scoring. | 2 |
| 2.3 | LLM-based extraction (hybrid) | For ambiguous sections: use OpenRouter API. Opt-in via `--use-llm` flag. Cache results. Graceful fallback to rule-based on API failure. Cost estimate in docs. | 2 |
| 2.4 | Interactive converter | After extraction: show extracted intent, highlight low-confidence fields (yellow) and missing fields (red), prompt user to confirm/correct each. `--interactive` flag (default for `--from`). `--yes` to skip. | 2 |
| 2.5 | `intentspec init --from AGENTS.md` | Parse -> extract -> interactive review -> generate intent.yaml + diff output. Per-field confidence scores in comments. | 1.5 |
| 2.6 | SKILL.md parser | Parse agentskills SKILL.md format: YAML frontmatter (name, description, version) + Markdown body (overview -> goals, instructions -> constraints, notes -> non_negotiables). | 2 |
| 2.7 | `intentspec init --from SKILL.md` | Parse SKILL.md -> extract -> interactive review -> generate intent.yaml | 1 |
| 2.8 | `intentspec init --from agentskills` | Parse agentskills registry format (same as SKILL.md). First-class support, not an afterthought. | 1.5 |
| 2.9 | `--quickstart` wizard | 3 interactive questions -> minimal intent.yaml. Questions: (1) What does the agent do? [-> goals] (2) What must it never do? [-> non_negotiables, severity: hard] (3) What tools does it use? [-> tools.allowed] | 1 |
| 2.10 | Converter accuracy benchmark | CI benchmark: run converter against 20 real files from spike, measure field-level accuracy. Target: 85%+ before W2 sign-off. Track per-field scores. | 1 |
| 2.11 | Tests: converter | Test against 20 real files. Edge cases: empty, malformed, non-English, recursive refs, multiple agents. Accuracy benchmark test. | 3 |

**Week 2 gate:** Converter handles AGENTS.md, SKILL.md, and agentskills. Interactive review works. Accuracy benchmark >= 70% (improving toward 85%). Tests pass.

### Week 3: Diff + Coverage + Score

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 3.1 | `intentspec diff` | Git integration: `git diff` for intent.yaml. Show added/removed/changed sections. `--semantic` flag: intent-level changes (goal X removed, constraint Y relaxed) using Intent model comparison. Graceful fallback when git unavailable: diff against cached `.intentspec/cache/`. Handle: shallow clones, detached HEAD, empty repos, monorepos. | 3 |
| 3.2 | `intentspec coverage` (structural) | AGENTS.md: count tools mentioned vs tools in `intent.tools.allowed`. SKILL.md: same. agentskills: same. Output: coverage % + missing tools list. Position as "estimate" (~73%). `--format` support. | 3 |
| 3.3 | `intentspec score` | IDS 0-100 with explicit formula (see § above). `--by-agent` breakdown. `--weights` flag for custom weighting. `--format` support. | 3 |
| 3.4 | Coverage/score output formatter | Per-agent breakdown, missing tools list, color-coded score (green >80, yellow 50-80, red <50). `--format json|yaml|text`. | 1.5 |
| 3.5 | `intentspec lint` | Quality checks (not a full linting engine): goal descriptions > 10 chars, constraints have enforceable field, tools have rationale, non-negotiables have severity, no duplicate tool names. `--format` support. | 1.5 |
| 3.6 | Tests: diff, coverage, score, lint | Edge cases: empty files, unicode, missing git, malformed yaml, large files (>1MB warning, >10MB error), symlinks, read-only filesystem. Performance: validate < 100ms for 50-intent file, diff < 500ms for 100-commit history, score < 200ms. | 4 |

**Phase 1 Gate:** All 6 commands work end-to-end (validate, init x3, diff, coverage, score, lint). Converter accuracy >= 70%. 50+ tests. 85%+ coverage. Schema matches BEST-PRACTICES research.

---

## Phase 2: CI/CD + Compliance + First Adapter (Weeks 4-5)

### Week 4: CI/CD Integration

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 4.1 | `intentspec ci` command | Exit codes: 0=pass, 1=validation error, 2=warning (stale/sparse), 3=below threshold. `--min-coverage N`, `--strict` (fail on warnings), `--format json`. Idempotent and stateless. | 2 |
| 4.2 | CI config flags | `--min-coverage N`, `--strict`, `--format json|yaml|text`, `--config PATH`. Documented precedence. | 1 |
| 4.3 | GitHub Action | `action.yml`: runs `intentspec ci`, posts PR comment with score + coverage. Test in a test repo. | 2.5 |
| 4.4 | GitLab CI template | `.gitlab-ci.yml` example job | 0.5 |
| 4.5 | Pre-commit hook | `pre-commit` config for local validation. Staged-only validation. | 0.5 |
| 4.6 | Generic CI guide | Document how to use `intentspec ci` in any CI system (Jenkins, CircleCI, Azure DevOps, etc.) using exit codes. | 0.5 |
| 4.7 | Tests: CI | All exit codes, flag combinations, JSON output, idempotency, concurrent runs. | 2 |

**Week 4 gate:** `intentspec ci` returns correct exit codes. GitHub Action works in test repo. Pre-commit hook works.

### Week 5: Compliance + Templates + CrewAI Adapter + Docs

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 5.1 | `intentspec audit-report` | Generate markdown compliance document: agent name, version, all specs, timestamp, hash. `--format json|yaml|text`. | 2 |
| 5.2 | Report template | SOC 2 / EU AI Act preamble, agent inventory table, version history, IDS trend. | 1.5 |
| 5.3 | 5 intent templates | coding-agent, research-agent, service-agent, data-pipeline, multi-agent-coordinator. Each uses full v1 schema. Stored in `src/intentspec/templates/`. | 2 |
| 5.4 | `intentspec init --template NAME` | Copy template to cwd, prompt for agent name. `template list` command. `init --template <url>` for community templates. | 1 |
| 5.5 | CrewAI adapter | Parse `crewai.yaml` -> extract Task.goal, Agent.role, Agent.backstory -> intent.yaml. `init --from crewai.yaml`. Read-only in v1 (no write-back). | 3 |
| 5.6 | Tests: audit-report, templates, CrewAI | Each template validates. CrewAI adapter tested on 3+ real configs. | 2 |
| 5.7 | Documentation site | `docs/` with mkdocs: installation, commands, schema reference, examples, CI integration, adapter guide. | 3 |
| 5.8 | README | Quickstart, badges, install, 3-command demo, config file reference. | 0.5 |

**Phase 2 Gate:** ci returns correct exit codes. audit-report generates. GitHub Action works. 5 templates validate. CrewAI adapter works on 3+ real configs. Docs site works locally. 70+ tests. 88%+ coverage.

---

## Phase 3: Publish + Integrate (Weeks 6-7)

### Week 6: Testing + Packaging

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 6.1 | Expand test suite | Target: 90%+ coverage, 80+ tests. Per-module minimums: validate/score/diff 95%+, converters 80%+, CLI glue 70%+. Risk-weighted coverage tracking. | 4 |
| 6.2 | Edge case testing | Unicode (emoji in all fields), large files, deeply nested YAML, concurrent runs, symlinks, read-only filesystem, network failures (LLM), shallow git clones. | 2 |
| 6.3 | Performance testing | Assert budgets: validate < 100ms (50-intent file), diff < 500ms (100-commit history), score < 200ms. CI assertions. | 1 |
| 6.4 | Converter improvement iteration | Run accuracy benchmark. Target: 85%+. Fix worst-performing extraction patterns. | 2 |
| 6.5 | `pyproject.toml` finalization | Version, classifiers, URLs, license (MIT). Pin all deps with version ranges. | 0.5 |
| 6.6 | Lock file | Generate `requirements.lock` via `pip-compile`. CI installs from lock file. | 0.5 |
| 6.7 | Security audit | Run `pip-audit` on all deps. Document results. Pin known-good versions. | 0.5 |
| 6.8 | Build + test on clean venv | `pip install -e .`, run all commands, run all tests. Python 3.11, 3.12, 3.13. | 1 |

**Week 6 gate:** 90%+ test coverage. All performance budgets met. Converter >= 75%. Security audit clean. Clean venv install works on 3 Python versions.

### Week 7: PyPI + Integrations + Beta

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 7.1 | TestPyPI publish | `python -m build && twine upload --repository testpypi dist/*`. Install from TestPyPI in clean venv. Run full test suite. | 0.5 |
| 7.2 | TestPyPI validation gate | All 9 commands work from TestPyPI install. All tests pass. No import errors. Only proceed to PyPI if all checks pass. | 0.5 |
| 7.3 | PyPI publish v0.1.0 | `twine upload dist/*`. | 0.5 |
| 7.4 | Smoke test published package | `pip install intentspec`, run all commands on sample repo. | 0.5 |
| 7.5 | Beta program | Recruit 5-10 beta users (from agent dev communities). Collect feedback via GitHub Issues. Fix critical issues. Use `dogfood` skill on own tool. | 3 |
| 7.6 | eval-harness integration | Cross-link: intent specs as eval dimensions. Document integration pattern. | 1 |
| 7.7 | agent-guard integration | Cross-link: intent specs document rationale for permissions. Document integration pattern. | 1 |

**Phase 3 Gate:** `pip install intentspec` from PyPI works. All 9 commands functional E2E. 90%+ test coverage. CI passing. Beta feedback incorporated.

---

## Phase 4: Harden + Launch (Weeks 8-10)

### Week 8: Remaining Framework Adapters + Health

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 8.1 | LangGraph adapter | Parse state graph -> extract node descriptions -> goals. `init --from langgraph.yaml`. | 2.5 |
| 8.2 | AutoGen adapter | Parse `system_message` -> extract goals/constraints. `init --from autogen-config.yaml`. | 2 |
| 8.3 | OpenAI Agents SDK adapter | Parse `Agent.instructions`, `Guardrail` -> intent.yaml. `init --from openai-agents.yaml`. | 2 |
| 8.4 | `intentspec health` command | Terminal dashboard: coverage trend, stale intents (>30 days), orphaned specs, IDS distribution. `--format json`. | 2.5 |
| 8.5 | Tests: adapters + health | Each adapter tested on 3+ real configs. Health command tested with mock data. | 2 |

**Week 8 gate:** 4 framework adapters working. Health command works. 80+ tests.

### Week 9: Dashboard + Launch Prep

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 9.1 | `intentspec dashboard --serve` | FastAPI + Jinja2 local server. Chart.js for trends (bundled locally, no CDN). Port auto-increment (8080, 8081...). `--host` flag for reverse proxy. | 4 |
| 9.2 | Drift detection (basic) | Compare intent.yaml mtime vs git log for agent files. Flag stale >30 days. `intentspec drift` command. | 2 |
| 9.3 | Tests: dashboard + drift | API endpoints, chart data, drift detection accuracy. Offline mode test. | 1.5 |
| 9.4 | Format validation | Test schema with 5+ real agent configs. Iterate schema if needed. Document findings. | 2 |
| 9.5 | Launch blog post | "IntentSpec: Test coverage for agent behavior" — positioning, demo, install. | 2 |
| 9.6 | HN/Reddit/Twitter prep | Draft posts, identify communities, prepare demo GIF. | 1 |

**Week 9 gate:** Dashboard serves locally. Drift detection flags stale intents. Blog post drafted. Demo ready.

### Week 10: Buffer + Launch

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 10.1 | Buffer | Unknown unknowns, bug fixes, polish. This is the riskiest phase — it deserves the most buffer. | 20 |
| 10.2 | Launch | Publish blog post. HN/Reddit/Twitter. Monitor feedback. Fix critical issues. | 4 |
| 10.3 | Post-launch | Respond to issues. Merge first community PRs. Publish "Intent Debt Report" (scan 100 popular agent repos). | 4 |

**Phase 4 Gate:** v1.0 launched. Blog post live. All 4 adapters working. Dashboard serves. 90%+ coverage. 80+ tests.

---

## Total Effort Estimate

| Phase | Weeks | Hours | Key Deliverable |
|-------|-------|-------|-----------------|
| Phase 1: Core CLI + Spec | 1-3 | ~44 | validate, init (AGENTS.md + SKILL.md + agentskills), diff, coverage, score, lint |
| Phase 2: CI/CD + Compliance + Adapter | 4-5 | ~30 | ci, audit-report, 5 templates, CrewAI adapter, docs |
| Phase 3: Publish + Integrate | 6-7 | ~22 | PyPI, TestPyPI gate, beta program, integrations |
| Phase 4: Harden + Launch | 8-10 | ~44 | 3 more adapters, dashboard, drift, launch |
| **Total** | **10 weeks** | **~140h** | **v1.0 launch** |

---

## Success Criteria

### Quality Metrics
- Test coverage: 90%+ (per-module minimums: core 95%+, converters 80%+)
- Converter accuracy: >= 75% on 20 real files (up from 60% baseline)
- Performance: validate < 100ms, diff < 500ms, score < 200ms
- Security: `pip-audit` clean, all deps pinned

### Adoption Metrics (3-month targets)
- GitHub stars: 500+
- PyPI downloads: tracked from v1
- CI/CD integrations: 50+ repos using Action
- Framework adapters: 4 (CrewAI, LangGraph, AutoGen, OpenAI)
- Community templates: 5+ contributed

### Process Metrics
- Beta users before launch: 5-10
- TestPyPI validation gate passed before PyPI
- All 9 commands work from PyPI install before blog post

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Converter accuracy < 75% | Interactive review as fallback. Ship converter as "beta" with human review flags. Accuracy benchmark in CI. |
| Timeline overrun (solo) | Drop Phase 4 W9-10 features if behind. Core MVP = Phase 1-3 only. W10 is pure buffer. |
| agentskills adds coverage scoring | Differentiate on compliance audit reports + CI enforcement. Position as complement. |
| Schema needs v2 before Phase 4 | Reserved fields (sub_agents, extends) in v1. Additive-only evolution policy. |
| Low adoption | Lead with compliance angle (SOC 2, EU AI Act). Target teams with agent incidents. Beta program for early feedback. |
| Dependency breakage | Lock file + version ranges. `pip-audit` in CI. Test against Python 3.11/3.12/3.13. |
| LLM extraction costs | Opt-in only. Rule-based is primary. Cache results. Document costs. |

---

## File Tree (REVISED)

```
workspace/
├── AGENTS.md
├── plan.md
├── pyproject.toml
├── requirements.lock              # NEW: reproducible builds
├── src/
│   └── intentspec/
│       ├── __init__.py
│       ├── cli.py                 # Click entry point
│       ├── models/
│       │   ├── __init__.py
│       │   └── intent.py          # NEW: Intent dataclass (all commands use this)
│       ├── spec/
│       │   ├── __init__.py
│       │   ├── schema.py          # intent.yaml JSON Schema (full v1)
│       │   ├── validate.py        # validate + semantic checks
│       │   └── formatter.py       # Error/output formatting
│       ├── converter/
│       │   ├── __init__.py
│       │   ├── agents_md.py       # AGENTS.md → intent.yaml
│       │   ├── skill_md.py        # SKILL.md → intent.yaml
│       │   ├── agentskills.py     # NEW: agentskills → intent.yaml
│       │   ├── quickstart.py      # Interactive wizard
│       │   ├── llm_extract.py     # LLM-based extraction (opt-in)
│       │   └── interactive.py     # NEW: interactive review flow
│       ├── coverage/
│       │   ├── __init__.py
│       │   ├── analyzer.py        # Coverage calculation
│       │   └── formatter.py       # Coverage output
│       ├── score/
│       │   ├── __init__.py
│       │   ├── ids.py             # Intent Debt Score (explicit formula)
│       │   └── formatter.py       # Score output
│       ├── ci/
│       │   ├── __init__.py
│       │   ├── checker.py         # CI command logic
│       │   └── report.py          # Compliance audit report
│       ├── adapters/              # NEW: framework adapters
│       │   ├── __init__.py
│       │   ├── crewai.py          # CrewAI adapter
│       │   ├── langgraph.py       # LangGraph adapter
│       │   ├── autogen.py         # AutoGen adapter
│       │   └── openai_agents.py   # OpenAI Agents SDK adapter
│       ├── dashboard/             # NEW: Phase 4 dashboard
│       │   ├── __init__.py
│       │   ├── app.py             # FastAPI app
│       │   └── templates/         # Jinja2 templates (Chart.js bundled)
│       └── templates/
│           ├── coding-agent.yaml
│           ├── research-agent.yaml
│           ├── service-agent.yaml
│           ├── data-pipeline.yaml
│           └── multi-agent-coordinator.yaml
├── action/
│   └── action.yml
├── docs/
│   └── ...                        # mkdocs documentation
└── tests/
    ├── test_cli.py
    ├── test_validate.py
    ├── test_semantic.py           # NEW: semantic validation tests
    ├── test_converter.py
    ├── test_agentskills.py        # NEW: agentskills converter tests
    ├── test_coverage.py
    ├── test_score.py
    ├── test_ci.py
    ├── test_lint.py               # NEW: lint command tests
    ├── test_adapters.py           # NEW: framework adapter tests
    ├── test_dashboard.py          # NEW: dashboard tests
    ├── benchmark_converter.py     # NEW: converter accuracy benchmark
    └── fixtures/
        ├── valid_intent.yaml
        ├── invalid_intent.yaml
        ├── sample_agents_md/
        │   ├── simple.md
        │   ├── complex.md
        │   └── minimal.md
        ├── sample_skills_md/      # NEW: SKILL.md fixtures
        │   ├── simple.md
        │   └── complex.md
        └── sample_agentskills/    # NEW: agentskills fixtures
            ├── simple.md
            └── complex.md
```

---

*Plan v2 derived from PDD v14 + BEST-PRACTICES.md + FEASIBILITY.md + product-deliberation-report.md + subagent audit (47 findings). All scope decisions trace to research. Timeline: 10 weeks solo developer, ~140 hours.*
