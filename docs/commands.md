# Commands Reference

Full reference for all IntentSpec CLI commands.

## Global Options

All commands support `--format text|json|yaml` (default: text).

## validate

Validate intent.yaml against JSON Schema v1 and semantic rules.

```bash
intentspec validate [PATH] [--strict] [--format text|json|yaml]
```

**Arguments:**
- `PATH` — File or directory to validate (default: current directory)

**Options:**
- `--strict` — Treat semantic warnings as errors (exit code 2)
- `--format` — Output format: text (default), json, yaml

**Exit codes:**
| Code | Meaning |
|------|---------|
| 0 | All files valid |
| 1 | Schema validation error |
| 2 | Semantic warning (only with `--strict`) |

**Examples:**
```bash
# Validate current directory
intentspec validate

# Validate a specific file
intentspec validate path/to/intent.yaml

# Strict mode — fail on warnings too
intentspec validate --strict

# Machine-readable output
intentspec validate --format json
```

---

## init

Initialize intent.yaml from an existing spec, template, or interactive wizard.

```bash
intentspec init [SOURCE] [OPTIONS]
```

### From Existing Spec

```bash
# Auto-detect format from file content
intentspec init --from AGENTS.md ./AGENTS.md
intentspec init --from SKILL.md ./my-skill/SKILL.md
intentspec init --from agentskills ./my-skill-directory/
intentspec init --from crewai ./crewai.yaml
```

### From Template

```bash
# List available templates
intentspec init --template list

# Use a template (prompts for agent name)
intentspec init --template coding-agent

# Use a template with explicit name (non-interactive)
intentspec init --template data-pipeline --name my-etl --output intent.yaml

# Community templates (placeholder)
intentspec init --template https://example.com/template.yaml
```

### Interactive Wizard

```bash
intentspec init --quickstart
```

The wizard prompts for:
1. Agent name (kebab-case)
2. Agent description (one sentence)
3. Agent type (coding/research/service/data/coordinator/custom)
4. Non-negotiables (comma-separated, or skip)
5. Tools (comma-separated, or skip)

### Options

| Option | Description |
|--------|-------------|
| `--from FORMAT` | Force input format: agents_md, skill_md, agentskills, crewai |
| `--template NAME` | Use built-in template, or `list` to see available |
| `--quickstart` | Run interactive wizard |
| `--use-llm` | Augment with LLM extraction (opt-in, cached) |
| `-o, --output PATH` | Output path (default: intent.yaml, `-` for stdout) |
| `--name NAME` | Override agent name (skips prompt, non-interactive) |
| `--interactive/--no-interactive` | Control interactive review (default: on for TTY) |
| `-y, --yes` | Skip interactive review |
| `--format FORMAT` | Output format: text (default), json, yaml |
| `--strict` | Refuse to write if validation fails |
| `--force` | Overwrite existing output file |

---

## score

Calculate Intent Debt Score (IDS 0-100).

```bash
intentspec score [PATH] [--by-agent] [--weights JSON] [--format text|json|yaml]
```

The IDS measures how complete and consistent an agent's intent specification is. Higher is better.

**IDS Formula:**
```
IDS = 100 - (
  tool_coverage    × 0.25 +
  goal_coverage    × 0.15 +
  constraint_cov   × 0.10 +
  non_negot_cov    × 0.15 +
  freshness        × 0.10 +
  completeness     × 0.15 +
  consistency      × 0.10
)
```

**Components:**

| Component | Weight | Measures |
|-----------|--------|----------|
| Tool coverage | 25% | Are all mentioned tools declared in intent? |
| Goal coverage | 15% | Are source goals reflected in intent? |
| Constraint coverage | 10% | Ratio of enforceable constraints |
| Non-negotiable coverage | 15% | Ratio of hard non-negotiables |
| Freshness | 10% | How recently was the spec updated? |
| Completeness | 15% | 8 fields: desc, goals, constraints, non-negotiables, tools_allowed, boundaries, escalation, failure_modes |
| Consistency | 10% | No tool in both allowed and denied lists |

**Options:**
- `--by-agent` — Show per-agent breakdown (for multi-agent specs)
- `--weights JSON` — Custom weights as JSON, e.g. `'{"tool_coverage":0.3}'`
- `--format` — Output format: text (default), json, yaml

---

## coverage

Show intent coverage percentage against source text.

```bash
intentspec coverage [PATH] [--format text|json|yaml]
```

Compares the intent.yaml against the original source text (AGENTS.md, SKILL.md, etc.) to determine what percentage of mentioned tools, goals, and constraints are captured in the formal intent spec.

**Output includes:**
- Overall coverage percentage
- Tool coverage (mentioned vs declared)
- Goal coverage (mentioned vs declared)
- Constraint coverage
- Non-negotiable coverage
- Missing tools list
- Missing goals list

---

## diff

Show intent changes between commits or against a source commit.

```bash
intentspec diff [PATH] [--semantic] [--source-commit HASH] [--format text|json|yaml]
```

**Options:**
- `--semantic` — Show intent-level changes (goals added/removed, tools changed) rather than raw text diff
- `--source-commit HASH` — Compare current state against a specific commit
- `--cache` — Use cached diff if git is unavailable
- `--format` — Output format: text (default), json, yaml

**Examples:**
```bash
# Show changes since last commit
intentspec diff intent.yaml

# Semantic diff — what changed in intent
intentspec diff --semantic

# Compare against a specific commit
intentspec diff --source-commit abc1234

# Machine-readable
intentspec diff --semantic --format json
```

---

## lint

Quality checks for intent specs. Not a full linting engine — focuses on common mistakes.

```bash
intentspec lint [PATH] [--format text|json|yaml]
```

**Checks performed:**
| Check | Description |
|-------|-------------|
| Goal description length | Goals should be > 10 characters |
| Constraint enforceable | Constraints should have enforceable: true/false |
| Tool rationale | Tools should have a rationale explaining why |
| Non-negotiable severity | Non-negotiables should have severity: hard/soft |
| Duplicate tool names | No tool should appear twice in allowed or denied |
| Agent description | Agent description should be > 10 characters |

**Exit codes:**
| Code | Meaning |
|------|---------|
| 0 | No issues found |
| 1 | Lint errors found |
| 2 | Warnings found |

---

## ci

CI/CD hook — runs validate + lint + score + coverage in one pass.

```bash
intentspec ci [PATH] [--min-coverage N] [--strict] [--format text|json|yaml]
```

Designed for CI/CD pipelines. Returns a single exit code representing the worst result from all checks.

**Exit codes:**
| Code | Meaning |
|------|---------|
| 0 | All checks pass |
| 1 | Validation error (schema/semantic/lint error) |
| 2 | Warning (stale, sparse) |
| 3 | Below threshold or missing spec |

**Options:**
- `--min-coverage N` — Minimum coverage threshold (0-100). Exit 3 if below.
- `--strict` — Treat warnings as errors (promotes exit 2 to exit 1)
- `--format` — Output format: text (default), json, yaml

**CI Configuration:**

Create `.intentspec.yaml` in your repo root:
```yaml
min_coverage: 80
strict: false
format: json
```

Config precedence: CLI flags > env vars > .intentspec.yaml > defaults

**GitHub Actions:**
```yaml
- uses: onicarps/intentspec-action@v1
  with:
    min-coverage: 80
    strict: true
```

**GitLab CI:**
```yaml
intentspec:
  script:
    - pip install intentspec
    - intentspec ci --min-coverage 80 --strict
```

---

## audit-report

Generate a compliance audit report for regulatory frameworks.

```bash
intentspec audit-report [PATH] [--format text|json|yaml]
```

Produces a comprehensive compliance document including:
- Agent inventory table (name, type, description, version)
- Full intent specification dump
- IDS score with component breakdown
- Version history placeholder
- SOC 2 / EU AI Act preamble
- Generation timestamp and SHA-256 hash of source file

**Options:**
- `--format` — Output format: text (markdown, default), json, yaml

**Example output (text):**
```
# IntentSpec Compliance Report

This report documents the declared intent of an AI agent to support
compliance evidence under frameworks such as SOC 2...

## Agent Inventory
| Name | Type | Description | Version |
| code-reviewer | coding | Reviews PRs for quality | 1.0 |

## Intent Specification
### Goals
- [high] Identify bugs, security vulnerabilities

## Intent Debt Score
IDS: ~96 / 100 (estimate)

---
Generated: 2026-06-20T08:00:00+00:00
SHA-256: a1b2c3d4...
```
