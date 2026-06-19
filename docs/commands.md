# Commands

## validate

Validate intent.yaml against schema and semantic rules.

```bash
intentspec validate [PATH] [--strict] [--format text|json|yaml]
```

**Exit codes:**
- `0` — Valid
- `1` — Schema validation error
- `2` — Semantic warning (use `--strict` to fail on warnings)

## init

Initialize intent.yaml from an existing spec, template, or interactive wizard.

```bash
# From existing spec
intentspec init --from AGENTS.md <path>
intentspec init --from SKILL.md <path>
intentspec init --from agentskills <path>
intentspec init --from crewai.yaml <path>

# From template
intentspec init --template coding-agent
intentspec init --template data-pipeline --name my-pipeline
intentspec init --template list

# Interactive wizard
intentspec init --quickstart
```

## score

Calculate Intent Debt Score (IDS 0-100).

```bash
intentspec score [PATH] [--by-agent] [--weights JSON] [--format text|json|yaml]
```

The IDS is calculated from 7 weighted components:

| Component | Weight |
|-----------|--------|
| Tool coverage | 25% |
| Goal coverage | 15% |
| Constraint coverage | 10% |
| Non-negotiable coverage | 15% |
| Freshness | 10% |
| Completeness | 15% |
| Consistency | 10% |

## coverage

Show intent coverage percentage.

```bash
intentspec coverage [PATH] [--format text|json|yaml]
```

## diff

Show intent changes between commits.

```bash
intentspec diff [PATH] [--semantic] [--source-commit HASH] [--format text|json|yaml]
```

## lint

Quality checks for intent specs.

```bash
intentspec lint [PATH] [--format text|json|yaml]
```

Checks: goal description length, constraint enforceability, tool rationale, non-negotiable severity, duplicate tools, agent description.

## ci

CI/CD hook — runs validate + lint + score + coverage in one pass.

```bash
intentspec ci [PATH] [--min-coverage N] [--strict] [--format text|json|yaml]
```

**Exit codes:**
- `0` — All checks pass
- `1` — Validation error
- `2` — Warning (stale/sparse)
- `3` — Below threshold or missing spec

## audit-report

Generate a compliance audit report.

```bash
intentspec audit-report [PATH] [--format text|json|yaml]
```

Produces a SOC 2 / EU AI Act compliance document with agent inventory, full spec dump, IDS score, and SHA-256 hash.
