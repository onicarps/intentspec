# AGENTS.md — IntentSpec Build Profile

**This file is the Droid's primary input for code generation. Be specific and complete.**

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
| CLI framework | Click | Standard, well-dested, easy testing |
| YAML parsing | PyYAML | Standard, handles all YAML 1.2 |
| Validation | jsonschema | JSON Schema for intent.yaml validation |
| Testing | pytest + pytest-cov | Industry standard, 90%+ target |
| Packaging | setuptools (pyproject.toml) | Modern, PEP 621 compliant |
| HTTP (converter LLM) | urllib.request | stdlib, no extra deps |
| Dashboard (Phase 4) | FastAPI + Jinja2 + Chart.js | Lightweight, no React needed |

---

## File Tree

```
~/.hermes/profiles/intentspec/
├── SOUL.md                    # Profile mission
├── AGENTS.md                  # THIS FILE - build spec
├── .env                       # Secrets (never commit)
├── profile.yaml               # Hermes profile config
├── memories/
│   └── MEMORY.md              # Build profile memory
├── workspace/                 # WORKING CODE LIVES HERE
│   ├── AGENTS.md              # Workspace-level spec (copy of this)
│   ├── plan.md                # Implementation plan
│   ├── pyproject.toml         # Package config
│   ├── src/
│   │   └── intentspec/
│   │       ├── __init__.py
│   │       ├── cli.py         # Click entry point, all commands
│   │       ├── spec/
│   │       │   ├── __init__.py
│   │       │   ├── schema.py       # intent.yaml JSON Schema
│   │       │   ├── validate.py     # validate command logic
│   │       │   └── formatter.py    # Error/output formatting
│   │       ├── converter/
│   │       │   ├── __init__.py
│   │       │   ├── agents_md.py    # AGENTS.md → intent.yaml
│   │       │   ├── skill_md.py     # SKILL.md → intent.yaml
│   │       │   ├── quickstart.py   # Interactive wizard
│   │       │   └── llm_extract.py  # LLM-based extraction (hybrid)
│   │       ├── coverage/
│   │       │   ├── __init__.py
│   │       │   ├── analyzer.py     # Coverage calculation
│   │       │   └── formatter.py    # Coverage output formatting
│   │       ├── score/
│   │       │   ├── __init__.py
│   │       │   ├── ids.py          # Intent Debt Score (0-100)
│   │       │   └── formatter.py    # Score output
│   │       ├── ci/
│   │       │   ├── __init__.py
│   │       │   ├── checker.py      # CI command logic
│   │       │   └── report.py       # Compliance audit report
│   │       └── templates/
│   │           ├── coding-agent.yaml
│   │           ├── research-agent.yaml
│   │           ├── service-agent.yaml
│   │           ├── data-pipeline.yaml
│   │           └── multi-agent-coordinator.yaml
│   ├── action/
│   │   └── action.yml         # GitHub Action definition
│   ├── docs/
│   │   └── ...                # mkdocs documentation
│   └── tests/
│       ├── test_cli.py
│       ├── test_validate.py
│       ├── test_converter.py
│       ├── test_coverage.py
│       ├── test_score.py
│       ├── test_ci.py
│       └── fixtures/
│           ├── valid_intent.yaml
│           ├── invalid_intent.yaml
│           └── sample_agents_md/
│               ├── simple.md
│               ├── complex.md
│               └── minimal.md
└── research/                   # Reference only (read-only)
    └── intentspec/
        └── ...                # All research artifacts
```

---

## MVP Commands (9 total)

```
intentspec validate [PATH]           # Validate intent.yaml against schema
intentspec init --from AGENTS.md     # Convert AGENTS.md → intent.yaml
intentspec init --from SKILL.md      # Convert SKILL.md → intent.yaml
intentspec init --quickstart         # Interactive wizard (3 questions)
intentspec diff [--from COMMIT]      # Show intent changes between commits
intentspec coverage [PATH]           # % of agent behavior covered by intent
intentspec score [--by-agent]        # Intent Debt Score (IDS 0-100)
intentspec ci [--min-coverage N]     # CI/CD hook with exit codes
intentspec audit-report [PATH]       # Generate compliance document
```

### Exit Codes for `intentspec ci`:
- `0` = pass (all specs valid, coverage above threshold)
- `1` = missing spec (no intent.yaml found)
- `2` = invalid spec (schema validation failed)
- `3` = below coverage threshold (only with `--min-coverage`)

---

## intent.yaml v1 Schema

```yaml
# intent.yaml v1.0
version: "1.0"                    # Required. Format version.

agent:                            # Required.
  name: string                    # Required. kebab-case identifier.
  type: enum                      # Required. One of: coding | research | service | data | coordinator | custom
  description: string             # Required. ≤200 chars.

intent:                           # Required.
  goals:                          # Optional.
    - description: string         # Required. What the agent achieves.
      priority: enum              # high | medium | low
      success_criteria: string    # Optional. How to measure.
  constraints:                    # Optional.
    - rule: string                # Required. The rule text.
      enforceable: boolean        # Required. true = hard rule, false = guideline.
  tools:                          # Optional.
    allowed: [string]             # List of allowed tools.
    denied: [string]              # List of denied tools.
  non_negotiables:                # Optional. Hard rules only.
    - rule: string                # Required.
      severity: enum              # hard | soft
```

---

## Testing Conventions

- **Framework:** pytest
- **Coverage target:** 90%+
- **Test location:** `workspace/tests/`
- **Fixtures:** `workspace/tests/fixtures/` (real AGENTS.md files, valid/invalid yaml)
- **Naming:** `test_<module>_<function>.py`
- **TDD rule:** Write test before source file for every new function
- **Run tests:** `cd workspace && python -m pytest -xvs`
- **Coverage:** `python -m pytest --cov=src/intentspec --cov-report=term-missing`

---

## Phase Gates

### Phase 1 Gate (Week 3)
- `intentspec validate` works on real intent.yaml files
- Converter handles AGENTS.md and SKILL.md with ≥60% accuracy
- `intentspec diff` shows changes between commits
- `intentspec coverage` produces structural coverage %
- `intentspec score` calculates IDS 0-100
- All tests pass: 50+ tests, 85%+ coverage

### Phase 2 Gate (Week 5)
- `intentspec ci` returns correct exit codes (0/1/2/3)
- `intentspec audit-report` generates markdown compliance doc
- GitHub Action works in test repo
- 5 intent templates ship
- Documentation site works locally

### Phase 3 Gate (Week 7)
- `pip install intentspec` from PyPI works
- All 9 commands functional end-to-end
- 90%+ test coverage, CI passing
- Integration cross-links with eval-harness and agent-guard

### Phase 4 Gate (Week 10)
- Framework adapters (CrewAI, LangGraph, AutoGen, OpenAI)
- Dashboard serves locally
- Format validation with 5+ real configs
- v1.0 launch-ready

---

## Code Conventions

- **Type hints:** All functions have type hints
- **Docstrings:** Google style for all public functions
- **Error handling:** Custom exceptions with helpful messages
- **Logging:** Click's built-in echo, no print() statements
- **Imports:** Absolute imports from `intentspec`
- **No external deps for core:** stdlib + Click + PyYAML + jsonschema only. LLM converter uses urllib (stdlib).

---

## Key Implementation Notes

1. **Converter is hybrid:** Rule-based for obvious patterns (NEVER/MUST → constraints, code blocks → tools). LLM-based for ambiguous sections. Output includes per-field confidence scores.

2. **Coverage is structural:** Count tools mentioned in AGENTS.md/SKILL.md vs tools declared in intent.yaml. NOT semantic analysis. Position as "estimate" in output.

3. **IDS formula:** coverage_pct × 0.4 + freshness_pct × 0.2 + completeness_pct × 0.2 + consistency_pct × 0.2 = IDS (0-100). 100 = fully documented.

4. **No database:** All operations are file-system based. No DB setup, no migrations.

5. **Git integration:** Use libgit2 or shell out to `git diff` for intent changes. Don't require git — work on plain directories too.

---

## Relationship to Research

The PDD at `research/intentspec/product-decision-doc.md` is the source of truth for scope. All implementation decisions should trace back to the PDD. When in doubt, check the PDD.

Do NOT implement features that are OUT of scope for MVP (see PDD §8). Specifically:
- NO linting rules engine in MVP (v1.1)
- NO framework adapters in MVP (Phase 4)
- NO behavioral drift detection (v2+)
- NO dashboard in MVP (Phase 4)
- NO VS Code extension (v1.1)

---

*AGENTS.md v1.0 — June 14 2026. Derrived from PDD v14. Ready for factory Droid.*
