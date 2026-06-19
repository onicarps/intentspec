# Mission: IntentSpec Week 5 — Compliance + Templates + CrewAI Adapter + Docs

## Your Task
Implement Week 5 of the IntentSpec project: audit-report command, 2 remaining templates, CrewAI adapter, template loading in init, docs site, and README. This completes Phase 2 (CI/CD + Compliance + First Adapter).

## Context: What Already Exists (334 tests passing)

### Source Code
- `src/intentspec/models/intent.py` — Intent dataclass with all sub-models
- `src/intentspec/spec/schema.py` — Complete JSON Schema v1
- `src/intentspec/spec/validate.py` — Schema + semantic validation
- `src/intentspec/spec/formatter.py` — Terminal output formatter
- `src/intentspec/converter/` — Full converter module (agents_md, skill_md, agentskills, interactive, llm_extract)
- `src/intentspec/score/ids.py` — IDS scoring engine (IdsResult, compute_ids)
- `src/intentspec/diff/__init__.py` — Diff module (git integration, semantic diff)
- `src/intentspec/lint/__init__.py` — Lint module (LintIssue, LintResult, lint_intent)
- `src/intentspec/coverage/__init__.py` + `analyzer.py` — Coverage analysis
- `src/intentspec/ci/__init__.py` (339L) — CI orchestration (run_ci, CiResult, CiCheckResult)
- `src/intentspec/ci/config.py` — Config loading (.intentspec.yaml, env vars, precedence)
- `src/intentspec/cli.py` (560L) — Click CLI with all commands; audit_report is a stub
- `src/intentspec/adapters/__init__.py` — empty, ready for CrewAI adapter
- `src/intentspec/templates/` — 3 templates done (coding-agent, research-agent, service-agent)
- `action/action.yml` — GitHub Action
- `.gitlab-ci.yml` — GitLab CI example
- `.pre-commit-hooks.yaml` — Pre-commit hook
- `docs/ci-integration.md` — CI integration guide

### Key APIs (from existing code)
- `validate_file(path) -> (Intent, schema_errors: list[str], semantic_warnings: list[str])`
- `compute_ids(intent, weights=None) -> IdsResult` with `.score`, `.breakdown`, `.to_json()`, `.to_yaml()`
- `lint_intent(intent) -> LintResult` with `.errors`, `.warnings`, `.to_dict()`, `.to_text()`
- `analyze_coverage(intent, source_path) -> CoverageResult` with `.overall` (0.0-1.0), `.to_dict()`, `.to_text()`
- `run_ci(paths, min_coverage, strict, output_format) -> CiResult` with `.to_json()`, `.to_yaml()`, `.to_text()`
- `converter_parse(path, use_llm, format) -> ParseResult` — the main converter entry point
- `parse_quickstart(answers: dict) -> ParseResult` — quickstart wizard

### Exit Code Standard
- `0` = success / pass
- `1` = validation error
- `2` = warning (stale, sparse)
- `3` = fatal (missing spec, below threshold)

## Week 5 Tasks

### 5.1: `intentspec audit-report` command
Create `src/intentspec/audit.py` with `generate_audit()` function that produces a compliance document:
- Agent name, version, all specs (goals, constraints, non-negotiables, tools, boundaries, escalation, failure_modes)
- Timestamp, content hash (SHA-256 of the file)
- IDS score summary
- `--format json|yaml|text` support
- Text format: markdown with sections (Agent Info, Intent Spec, Score, Version History placeholder)
- Wire into cli.py replacing the stub

### 5.2: Report template
The text output should include:
- Header: "IntentSpec Compliance Report"
- Agent inventory table (name, type, description, version)
- Full intent spec dump (all fields)
- IDS score with breakdown
- Version history section (placeholder for now)
- SOC 2 / EU AI Act preamble paragraph
- Footer: generation timestamp, file hash

### 5.3: 2 more intent templates
Create `src/intentspec/templates/data-pipeline.yaml` and `src/intentspec/templates/multi-agent-coordinator.yaml`.
Each uses the full v1 schema (all fields populated). Follow the format of existing templates (coding-agent.yaml).

**data-pipeline.yaml:**
- type: "data"
- goals: data ingestion, transformation, quality checks, pipeline monitoring
- constraints: schema validation, error handling, retry logic
- non-negotiables: no data loss, no PII in logs, no unapproved schema changes
- tools: allowed (spark, airflow, dbt, data_validation), denied (production_db_direct)
- boundaries: ETL pipelines, data quality; out_of_scope: ML model training, dashboard creation
- escalation: data quality threshold breach → notify data team
- failure_modes: silent data corruption → checksums; pipeline stall → timeout alerts

**multi-agent-coordinator.yaml:**
- type: "coordinator"
- goals: task decomposition, agent orchestration, result aggregation, conflict resolution
- constraints: respect agent autonomy, maintain audit trail, enforce timeouts
- non_negotiables: never bypass agent safety checks, never execute unverified sub-agent output
- tools: allowed (task_planner, agent_registry, message_bus), denied (direct_code_execution)
- boundaries: coordination logic; out_of_scope: actual task execution by sub-agents
- escalation: sub-agent failure cascade → human supervisor
- failure_modes: circular delegation → max depth limit; conflicting sub-agent outputs → voting/quorum

### 5.4: `intentspec init --template NAME`
Add template loading to the init command:
- `--template NAME` — copy template from `src/intentspec/templates/<NAME>.yaml` to cwd
- Prompt for agent name (replace template's agent.name)
- `--template list` — list available templates
- `--template <url>` — download from URL (placeholder: print "community templates coming soon")
- After copying, run validate on the result and report any issues
- Update cli.py init command to handle `--template` flag

### 5.5: CrewAI adapter
Create `src/intentspec/adapters/crewai.py` with `parse_crewai(path) -> ParseResult`:
- Parse `crewai.yaml` (CrewAI config format)
- Extract from agents: `role` → agent description, `backstory` → agent description supplement
- Extract from tasks: `goal` → intent goals, `description` → goal description
- Extract from tools: tool names → tools.allowed
- Map CrewAI agent `allow_delegation` → boundaries
- Return a ParseResult compatible with the converter pipeline
- Wire into `converter/__init__.py`: add `crewai` format detection (file named `crewai.yaml` or `crewai.yml`)
- Wire into cli.py init: add `crewai` to `--from` choices
- Read-only in v1 (no write-back to crewai.yaml)

Create 3+ test fixture files at `tests/fixtures/sample_crewai/`:
- `simple.yaml` — 2 agents, 2 tasks, basic tools
- `complex.yaml` — 4+ agents, multiple tasks, nested tool configs
- `minimal.yaml` — 1 agent, 1 task, no tools

### 5.6: Tests
Create/update test files:
- `tests/test_audit.py` — audit-report tests (text/json/yaml output, hash correctness, all sections present)
- `tests/test_templates.py` — validate all 5 templates pass schema validation
- `tests/test_adapters.py` — CrewAI adapter tests (parse simple/complex/minimal, verify intent fields)
- `tests/test_ci.py` — add tests for init --template if not already covered

### 5.7: Documentation site
Create `docs/` structure with mkdocs:
- `docs/index.md` — landing page with quickstart
- `docs/installation.md` — pip install, requirements
- `docs/commands.md` — all commands with examples
- `docs/schema.md` — full schema reference
- `docs/examples.md` — example intent.yaml files
- `docs/ci-integration.md` — (already exists, link to it)
- `docs/adapters.md` — adapter guide (CrewAI, future: LangGraph, AutoGen, OpenAI)
- `mkdocs.yml` — mkdocs config (theme: material or readthedocs)

### 5.8: README
Update `README.md` with:
- Badges (PyPI, CI, coverage, license)
- Quickstart (3-command demo: pip install, init --quickstart, validate)
- Feature list
- Link to docs
- Config file reference

## Constraints
- No new dependencies beyond stdlib + Click + PyYAML + jsonschema
- Type hints on all functions, Google-style docstrings
- All code must pass `python3 -m pytest tests/ -q`
- Follow existing code patterns
- TDD throughout (write tests first, then implementation)
- CrewAI adapter: read-only, graceful handling of missing fields

## File Structure to Create
```
src/intentspec/
  audit.py                    # generate_audit() function
  adapters/
    crewai.py                 # parse_crewai() function
  templates/
    data-pipeline.yaml        # data pipeline template
    multi-agent-coordinator.yaml  # multi-agent coordinator template
tests/
  test_audit.py               # audit-report tests
  test_templates.py           # template validation tests
  test_adapters.py            # CrewAI adapter tests
  fixtures/
    sample_crewai/
      simple.yaml
      complex.yaml
      minimal.yaml
docs/
  index.md
  installation.md
  commands.md
  schema.md
  examples.md
  adapters.md
mkdocs.yml
README.md (update)
```

## Verification
After implementation, run:
```bash
cd ~/.hermes/profiles/intentspec/workspace
pip install -e ".[dev]" --break-system-packages
python3 -m pytest tests/ -q
intentspec audit-report tests/fixtures/valid_intent.yaml
intentspec audit-report tests/fixtures/valid_intent.yaml --format json
intentspec init --template data-pipeline
intentspec init --template list
intentspec init --from tests/fixtures/sample_crewai/simple.yaml
```

All tests should pass. All 5 templates should validate. Audit report should produce valid output in all 3 formats.

## Phase 2 Gate (end of W5)
- ci returns correct exit codes
- audit-report generates valid output
- GitHub Action works
- 5 templates validate
- CrewAI adapter works on 3+ real configs
- Docs site works locally
- 70+ tests
- 88%+ coverage
