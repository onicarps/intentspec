# AGENTS.md — IntentSpec Build Profile

**This file is the Droid's primary input for code generation. Be specific and complete.**

## Project Status (canonical)

**Read `STATUS.md` in this directory first.**

| Phase | Version | Status |
|-------|---------|--------|
| 2A Core moat | v1.1.0 | ✅ COMPLETE |
| 2B Inner dev loop | v1.2.0 | ✅ COMPLETE — `test`, `watch`, `status`, `coverage --trend` |
| 2C Growth | v1.3.1 | ✅ COMPLETE — `report`, `/demo`, `analyze`, `gate`, QA fixes |
| 3 Publish + integrate | — | 🔜 **NEXT** — beta program, TestPyPI gate, deferred cuts |

PyPI: `intentspec==1.3.1` · Tests: 977 passing · Tag: `v1.3.1`

---

## Project Identity

- **Name:** IntentSpec
- **Package:** `intentspec` (PyPI)
- **CLI command:** `intentspec`
- **Repository:** github.com/onicarps/intentspec
- **License:** MIT
- **Python:** 3.11+

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| CLI framework | Click >=8.0,<9.0 | Standard, well-dested, easy testing |
| YAML parsing | PyYAML >=6.0,<7.0 | Standard, handles all YAML 1.2 |
| Validation | jsonschema >=4.0,<5.0 | JSON Schema draft-07 for intent.yaml |
| Testing | pytest + pytest-cov | Industry standard, 90%+ target |
| Packaging | setuptools (pyproject.toml) | Modern, PEP 621 compliant |
| HTTP (converter LLM) | urllib.request | stdlib, no extra deps |
| Dashboard (Phase 4) | FastAPI + Jinja2 + Chart.js | Lightweight, no React needed. Chart.js via CDN. |

---

## File Tree

```
workspace/
├── AGENTS.md
├── plan.md
├── pyproject.toml
├── requirements.lock              # Reproducible builds (pip-compile)
├── src/
│   └── intentspec/
│       ├── __init__.py
│       ├── cli.py                 # Click entry point, all commands
│       ├── models/
│       │   ├── __init__.py
│       │   └── intent.py          # Intent dataclass (all commands use this, not raw YAML)
│       ├── spec/
│       │   ├── __init__.py
│       │   ├── schema.py          # intent.yaml JSON Schema (full v1)
│       │   ├── validate.py        # validate + semantic checks
│       │   └── formatter.py       # Error/output formatting
│       ├── converter/
│       │   ├── __init__.py
│       │   ├── agents_md.py       # AGENTS.md → intent.yaml
│       │   ├── skill_md.py        # SKILL.md → intent.yaml
│       │   ├── agentskills.py     # agentskills → intent.yaml
│       │   ├── quickstart.py      # Interactive wizard (3 questions)
│       │   ├── llm_extract.py     # LLM-based extraction (opt-in, cached)
│       │   └── interactive.py     # Interactive review flow
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
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── crewai.py          # CrewAI adapter
│       │   ├── langgraph.py       # LangGraph adapter
│       │   ├── autogen.py         # AutoGen adapter
│       │   └── openai_agents.py   # OpenAI Agents SDK adapter
│       ├── dashboard/
│       │   ├── __init__.py
│       │   ├── app.py             # FastAPI app
│       │   └── templates/         # Jinja2 templates (Chart.js bundled locally)
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
    ├── test_semantic.py           # Semantic validation tests
    ├── test_converter.py
    ├── test_agentskills.py        # agentskills converter tests
    ├── test_coverage.py
    ├── test_score.py
    ├── test_ci.py
    ├── test_lint.py               # lint command tests
    ├── test_adapters.py           # Framework adapter tests
    ├── test_dashboard.py          # Dashboard tests
    ├── benchmark_converter.py     # Converter accuracy benchmark (CI)
    └── fixtures/
        ├── valid_intent.yaml
        ├── invalid_intent.yaml
        ├── sample_agents_md/
        │   ├── simple.md
        │   ├── complex.md
        │   └── minimal.md
        ├── sample_skills_md/
        │   ├── simple.md
        │   └── complex.md
        └── sample_agentskills/
            ├── simple.md
            └── complex.md
```

---

## MVP Commands (10 total)

```
intentspec validate [PATH]           # Validate intent.yaml (schema + semantic)
intentspec init --from AGENTS.md     # Convert AGENTS.md → intent.yaml (interactive)
intentspec init --from SKILL.md      # Convert SKILL.md → intent.yaml (interactive)
intentspec init --from agentskills   # Convert agentskills → intent.yaml (interactive)
intentspec init --from crewai.yaml   # Convert CrewAI config → intent.yaml (Phase 2)
intentspec init --template NAME      # From template (coding, research, service, etc.)
intentspec init --quickstart         # Interactive wizard (3 questions)
intentspec diff [--from COMMIT]      # Show intent changes (git or cache fallback)
intentspec coverage [PATH]           # % of agent behavior covered by intent (estimate)
intentspec score [--by-agent]        # Intent Debt Score (IDS 0-100)
intentspec lint                      # Quality checks (not full linting engine)
intentspec ci [--min-coverage N]     # CI/CD hook with exit codes
intentspec audit-report [PATH]       # Generate compliance document
intentspec health                    # Terminal dashboard (Phase 4)
intentspec dashboard --serve         # Local web dashboard (Phase 4)
intentspec drift                     # Detect stale intents (Phase 4)
```

### Exit Codes (ALL commands):
- `0` = success / pass
- `1` = validation error (schema or semantic)
- `2` = warning (stale, sparse — usable but suboptimal)
- `3` = fatal (missing spec, below threshold, unrecoverable)

### Output Format (ALL commands):
- `--format text` (default) — Human-readable terminal output with colors
- `--format json` — Machine-readable JSON to stdout
- `--format yaml` — YAML to stdout

---

## intent.yaml v1 Schema

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
# Examples: hipaa:, socaa:, gdpr:
```

### Schema Design Principles
- **Minimal core:** 5 required fields (version, agent.name, agent.type, agent.description, intent)
- **Additive evolution:** v1 fields never removed or renamed
- **enforceable boolean:** THE key design decision — splits automatable vs human-judged constraints
- **rationale on tools:** Every tool permission has a *why*
- **severity on non-negotiables:** hard = CI fail, soft = CI warning
- **failure_modes first-class:** Most specs only document what should happen
- **status lifecycle:** draft -> active -> deprecated (from DESIGN.md FSM)
- **additionalProperties: false** on all schema objects (typos caught, not silently ignored)

---

## IDS Formula (Explicit)

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
| tool_coverage | 25% | tools.allowed count / tools detected in source |
| goal_coverage | 15% | intent.goals count / goals detected in source |
| constraint_cov | 10% | enforceable:true constraints / total constraints |
| non_negot_cov | 15% | severity:hard non-negotiables / total non-negotiables |
| freshness | 10% | e^(-0.693 * days_since_update / 30) — 30-day half-life |
| completeness | 15% | Weighted ratio of populated optional fields |
| consistency | 10% | 100% if no conflicts, 0% if conflicts exist |

**Positioning:** IDS is an *estimate*. Display as `~73` not `73`.

---

## Testing Conventions

- **Framework:** pytest + pytest-cov
- **Coverage target:** 90%+ overall. Per-module minimums: core 95%+, converters 80%+, CLI glue 70%+
- **Test location:** `workspace/tests/`
- **Fixtures:** `workspace/tests/fixtures/` (real AGENTS.md, SKILL.md, agentskills files, valid/invalid yaml)
- **Naming:** `test_<module>_<function>.py`
- **TDD rule:** Write test before source file for every new function. Exception: W1 schema work may use spike-then-test.
- **Run tests:** `cd workspace && python -m pytest -xvs`
- **Coverage:** `python -m pytest --cov=src/intentspec --cov-report=term-missing`
- **Performance budgets:** validate < 100ms (50-intent file), diff < 500ms (100-commit), score < 200ms
- **Converter benchmark:** `tests/benchmark_converter.py` — CI test measuring field-level accuracy on 20 real files. Target: 75%+

---

## Phase Gates

> **Execution status (June 26 2026):** Phase 1 ✅ · Phase 2A ✅ · Phase 2B ✅ · Phase 2C ✅ · **Phase 3 next** · Phase 4 planned. See `STATUS.md`.

### Phase 1 Gate (Week 3) — ✅ MET
- `intentspec validate` works on 10+ sample files (schema + semantic)
- Converter handles AGENTS.md, SKILL.md, and agentskills with interactive review
- Converter accuracy >= 70% on benchmark (targeting 85%)
- `intentspec diff` works (git + cache fallback)
- `intentspec coverage` produces structural coverage estimate
- `intentspec score` calculates IDS 0-100 with explicit formula
- `intentspec lint` checks quality
- `.intentspec.yaml` config file works
- 50+ tests, 85%+ coverage

### Phase 2 Gate (Week 5) — ✅ MET (2A + 2B + 2C shipped v1.3.1)
- `intentspec ci` returns correct exit codes (0/1/2/3)
- `intentspec audit-report` generates markdown compliance doc
- GitHub Action works in test repo
- 5 intent templates ship and validate
- CrewAI adapter works on 3+ real configs
- Documentation site works locally
- 70+ tests, 88%+ coverage

### Phase 3 Gate (Week 7) — 🔜 NEXT
- TestPyPI validation gate passed (all 9+ commands work from TestPyPI install)
- PyPI publish v0.1.0
- Beta program: 5-10 users, feedback incorporated
- 90%+ test coverage, CI passing
- Integration cross-links with eval-harness and agent-guard

### Phase 4 Gate (Week 10)
- 4 framework adapters working (CrewAI, LangGraph, AutoGen, OpenAI)
- Dashboard serves locally (offline-capable)
- Drift detection flags stale intents
- v1.0 launched (blog post live, HN/Reddit/Twitter)
- 80+ tests, 90%+ coverage

---

## Code Conventions

- **Type hints:** All functions have type hints
- **Docstrings:** Google style for all public functions
- **Error handling:** Custom exceptions with helpful messages
- **Logging:** Click's built-in echo, no print() statements
- **Imports:** Absolute imports from `intentspec`
- **No external deps for core:** stdlib + Click + PyYAML + jsonschema only
- **LLM converter:** opt-in (--use-llm flag), cached, graceful fallback to rule-based
- **All commands operate on Intent model**, not raw YAML directly
- **Lock file:** requirements.lock generated via pip-compile, CI installs from lock
- **Security:** pip-audit in CI, all deps pinned with version ranges

---

## Key Implementation Notes

1. **Intent model is the core abstraction:** All commands (validate, score, diff, coverage, lint, ci, audit-report) operate on the `Intent` dataclass, not raw YAML. Schema changes only require updating the model + schema, not every command.

2. **Converter is hybrid + interactive:** Rule-based for high-precision fields (tools, hard constraints). LLM-based for nuanced extraction (goals, conditionals) — opt-in with `--use-llm`. Interactive review by default: show extracted intent, highlight low-confidence fields, prompt user to confirm/correct. `--yes` to skip.

3. **Coverage is structural, positioned as estimate:** Count tools/goals mentioned in AGENTS.md/SKILL.md/agentskills vs declared in intent.yaml. NOT semantic analysis. Display as `~73%` not `73%`.

4. **agentskills is a first-class input format:** Not deferred to v1.1. `init --from agentskills` ships in Phase 1 alongside AGENTS.md and SKILL.md.

5. **Schema evolution:** Reserved fields (sub_agents, extends) in v1 for Phase 4. Additive-only policy — v1 fields never removed or renamed. Schema registry maps version -> validation rules.

6. **No database:** All operations are file-system based. No DB setup, no migrations.

7. **Git integration with fallback:** `diff` command uses git when available, falls back to cached `.intentspec/cache/` when not. Handles shallow clones, detached HEAD, empty repos.

8. **Config file:** `.intentspec.yaml` in project root. Supports: default_format, strict_mode, min_coverage. Precedence: CLI flags > env vars > config > defaults.

9. **TestPyPI gate:** No direct PyPI publish. Must pass TestPyPI install + full test suite first.

10. **Beta before launch:** 5-10 external beta users before HN launch. Collect feedback via GitHub Issues. Fix critical issues before public announcement.

---

## Relationship to Research

The PDD at `research/intentspec/product-decision-doc.md` is the source of truth for scope. All implementation decisions should trace back to the PDD and its enrichment artifacts:

- `BEST-PRACTICES.md` — Schema design, IDS formula, coverage architecture
- `FEASIBILITY.md` — Scanning approaches, spec format examples, moat analysis
- `study-agentskills.md` — agentskills interoperability, progressive disclosure
- `study-formats.md` — DESIGN.md + soul.md patterns adopted
- `spike-converter-report.md` — Converter architecture, accuracy baseline
- `product-deliberation-report.md` — Positioning pivot, RICE score, preconditions

Do NOT implement features that are OUT of scope for MVP:
- NO linting rules engine in MVP (v1.1)
- NO LangGraph/AutoGen/OpenAI adapters in MVP (Phase 4)
- NO behavioral drift detection in MVP (Phase 4, basic only)
- NO dashboard in MVP (Phase 4)
- NO VS Code extension (v1.1)
- NO intent registry/marketplace (v1.1)

---

*AGENTS.md v2.0 — June 17 2026. Derived from PDD v14 + BEST-PRACTICES.md + FEASIBILITY.md + subagent audit (47 findings). Ready for factory Droid.*
