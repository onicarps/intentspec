# Implementation Plan — IntentSpec

**Created:** June 14 2026
**PDD Reference:** `research/intentspec/product-decision-doc.md`
**Timeline:** 10 weeks (solo developer)
**Stack:** Python, Click (CLI), PyYAML, jsonschema, pytest

---

## Phase 1: Core CLI + Spec Format (Weeks 1-3)

### Week 1: Project Scaffold + Spec Format

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 1.1 | `pyproject.toml` | Package: `intentspec`, entry point: `intentspec`, deps: click, pyyaml, jsonschema | 1 |
| 1.2 | Directory structure | `src/intentspec/{cli,spec,converter,coverage,score,ci}/` | 0.5 |
| 1.3 | `intentspec validate` command | Glob for `intent.yaml`, validate against JSON Schema, report errors with file:line | 3 |
| 1.4 | `intent.yaml` v1 JSON Schema | 5 core fields: version, agent, intent (goals, constraints), tools, non_negotiables. See PDD §4 | 2 |
| 1.5 | Error output formatter | Colored terminal output, file:line:col, suggestion hints | 1.5 |
| 1.6 | Tests: validate | 15+ tests: valid schema, missing fields, wrong types, malformed YAML | 2 |

**Week 1 gate:** `intentspec validate` works on real intent.yaml files. Tests pass.

### Week 2: Converter (AGENTS.md + SKILL.md)

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 2.1 | AGENTS.md parser | Extract sections (goals, constraints, tools, non-negotiables) via regex + heuristics | 4 |
| 2.2 | Rule-based extraction | NEVER/MUST/ALWAYS → constraints. Code blocks → tools. Section headers → goals | 3 |
| 2.3 | LLM-based extraction (hybrid) | For ambiguous sections: use OpenRouter API to extract structured intent | 3 |
| 2.4 | `intentspec init --from AGENTS.md` | Parse → extract → generate intent.yaml + diff output | 2 |
| 2.5 | SKILL.md parser | Parse agentskills SKILL.md format (name, description, capabilities → goals) | 3 |
| 2.6 | `intentspec init --from SKILL.md` | Parse SKILL.md → generate intent.yaml | 2 |
| 2.7 | `--quickstart` wizard | 3 interactive questions → minimal intent.yaml (Click prompts) | 1 |
| 2.8 | Tests: converter | Test against 20 real files from spike. ≥60% accuracy threshold. | 3 |

**Week 2 gate:** Converter handles AGENTS.md and SKILL.md. Accuracy ≥60% on spike test set.

### Week 3: Diff + Coverage + Score

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 3.1 | `intentspec diff` | Git integration: `git diff` for intent.yaml, show added/removed/changed sections | 3 |
| 3.2 | `intentspec coverage` (structural) | AGENTS.md: count tools mentioned vs tools in intent.yaml. SKILL.md: same. = coverage % | 4 |
| 3.3 | `intentspec score` | IDS 0-100: coverage (40%) + freshness (20%) + completeness (20%) + consistency (20%) | 3 |
| 3.4 | Coverage output formatter | Per-agent breakdown, missing tools list, color-coded score | 2 |
| 3.5 | Tests: diff, coverage, score | Edge cases: empty files, unicode, missing git, malformed yaml | 3 |

**Week 3 gate:** All 6 commands work end-to-end. Coverage produces reasonable numbers.

---

## Phase 2: CI/CD + Compliance (Weeks 4-5)

### Week 4: CI/CD Integration

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 4.1 | `intentspec ci` command | Exit codes: 0=pass, 1=missing spec, 2=invalid spec, 3=below threshold | 2 |
| 4.2 | CI config flags | `--min-coverage N`, `--strict` (fail on warnings), `--format json` | 2 |
| 4.3 | GitHub Action | `action.yml`: runs `intentspec ci`, posts PR comment with score | 3 |
| 4.4 | GitLab CI template | `.gitlab-ci.yml` example job | 1 |
| 4.5 | Pre-commit hook | `pre-commit` config for local validation | 1 |
| 4.6 | Tests: CI | All exit codes, flag combinations, JSON output | 2 |

**Week 4 gate:** GitHub Action works in a test repo. `intentspec ci` returns correct exit codes.

### Week 5: Compliance + Polish

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 5.1 | `intentspec audit-report` | Generate markdown compliance document: agent name, version, all specs, timestamp, hash | 3 |
| 5.2 | Report template | SOC 2 / EU AI Act preamble, agent inventory table, version history | 2 |
| 5.3 | 5 intent templates | coding-agent, research-agent, service-agent, data-pipeline, multi-agent-coordinator | 2 |
| 5.4 | `intentspec init --template NAME` | Copy template to cwd, prompt for agent name | 1 |
| 5.5 | Documentation site | `docs/` with mkdocs: installation, commands, schema, examples, CI integration | 4 |
| 5.6 | README | Quickstart, badges, install, 3-command demo | 1 |

**Week 5 gate:** Full documentation site live locally. Templates tested.

---

## Phase 3: Publish + Integrate (Weeks 6-7)

### Week 6: Testing + Packaging

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 6.1 | Expand test suite | Target: 90%+ coverage, 80+ tests | 5 |
| 6.2 | Edge case testing | Unicode, large files, deeply nested YAML, concurrent runs | 2 |
| 6.3 | Performance testing | 100-agent repos, <5s per command | 1 |
| 6.4 | `pyproject.toml` finalization | Version, classifiers, URLs, license (MIT) | 0.5 |
| 6.5 | Build + test on clean venv | `pip install -e .`, run all commands, run all tests | 1 |

**Week 6 gate:** `pip install intentspec` works. All tests pass on clean install.

### Week 7: PyPI + GitHub Action

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 7.1 | PyPI publish v0.1.0 | `python -m build && twine upload dist/*` | 1 |
| 7.2 | GitHub Action publish | Publish to GitHub Marketplace (or document manual install) | 2 |
| 7.3 | Smoke test published package | `pip install intentspec`, run all commands on sample repo | 1 |
| 7.4 | Frameit integration | Cross-link with eval-harness: intent specs as eval dimensions | 2 |
| 7.5 | agent-guard integration | Cross-link: intent specs document rationale for permissions | 1 |

**Week 7 gate:** `pip install intentspec` from PyPI works. GitHub Action installable.

---

## Phase 4: Harden + Launch Prep (Weeks 8-10)

### Week 8: Framework Adapters

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 8.1 | CrewAI adapter | Parse `crewai.yaml` → extract Task.goal, Agent.role → intent.yaml | 3 |
| 8.2 | LangGraph adapter | Parse state graph → extract node descriptions → goals | 3 |
| 8.3 | AutoGen adapter | Parse `system_message` → extract goals/constraints | 2 |
| 8.4 | OpenAI Agents SDK adapter | Parse `Agent.instructions` → intent.yaml | 2 |
| 8.5 | Tests: adapters | Each adapter tested on 3+ real configs | 2 |

**Week 8 gate:** 4 framework adapters working. `intentspec init --from crewai.yaml` etc.

### Week 9: Dashboard + Drift Detection

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 9.1 | `intentspec health` command | Terminal dashboard: coverage trend, stale intents, orphaned specs | 3 |
| 9.2 | `intentspec dashboard --serve` | FastAPI + Jinja2 local server, Chart.js for trends | 5 |
| 9.3 | Drift detection (basic) | Compare intent.yaml age vs git log for agent files. Flag stale >90 days | 2 |
| 9.4 | Tests: dashboard | API endpoints, chart data, drift detection accuracy | 2 |

**Week 9 gate:** Dashboard serves locally. Drift detection flags stale intents.

### Week 10: Launch Prep + Buffer

| # | Task | Detail | Hours |
|---|------|--------|-------|
| 10.1 | Format validation plan | Test with 5+ real agent configs (PDD §11). Iterate schema if needed. | 4 |
| 10.2 | Launch blog post | "IntentSpec: Test coverage for agent behavior" — positioning, demo, install | 3 |
| 10.3 | HN/Reddit/Twitter prep | Draft posts, identify communities, prepare demo GIF | 2 |
| 10.4 | Buffer | Unknown unknowns, bug fixes, polish | 8 |

**Week 10 gate:** v1.0 ready for public launch. Blog post drafted. Demo repo ready.

---

## Total Effort Estimate

| Phase | Weeks | Hours | Key Deliverable |
|-------|-------|-------|-----------------|
| Phase 1: Core CLI + Spec | 1-3 | ~40 | validate, init, diff, coverage, score |
| Phase 2: CI/CD + Compliance | 4-5 | ~25 | ci, audit-report, templates, docs |
| Phase 3: Publish + Integrate | 6-7 | ~20 | PyPI, GitHub Action, integrations |
| Phase 4: Harden + Launch | 8-10 | ~40 | adapters, dashboard, launch prep |
| **Total** | **10 weeks** | **~125h** | **v1.0 launch** |

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Converter accuracy <60% | Fallback to `--quickstart` wizard. Ship converter as "beta" with human review flags. |
| Timeline overrun (solo) | Drop Phase 4 Week 9-10 features if behind. Core MVP = Phase 1-3 only. |
| agentskills adds coverage scoring | Differentiate on compliance audit reports + CI enforcement. Pivot to "compliance layer." |
| Low adoption | Lead with compliance angle (SOC 2, EU AI Act). Target teams with agent incidents. |
| AGENTS.md format changes | Monitor OpenRouter/Anthropic releases. Version the converter. |

---

## Success Criteria (from PDD §6)

| Metric | 3-month target | 6-month target |
|--------|---------------|----------------|
| GitHub stars | 500+ | 2000+ |
| PyPI downloads | Tracked from v1 | — |
| CI/CD integrations | 50+ repos using Action | 200+ |
| Framework adapters | 1 (CrewAI) | 4+ |
| Test coverage | 90%+ | 90%+ |
| Converter accuracy | ≥60% | ≥70% |

---

*Plan derived from PDD v14 (June 14 2026). All scope decisions trace to product deliberation findings. Timeline: 10 weeks solo developer.*
