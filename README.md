# IntentSpec

**Coverage and enforcement layer for AI agent infrastructure.**

IntentSpec transforms agent development from ad-hoc documentation to versioned, testable, and enforceable intent. Document agent behavior as code, measure intent coverage, score intent debt, and enforce intent through CI/CD.

Works with any agent spec format — AGENTS.md, SKILL.md, agentskills, or CrewAI. Convert existing specs to a standardized `intent.yaml`, then validate, score, diff, lint, and enforce it in CI/CD.

## Quickstart

```bash
pip install intentspec

# Create a new spec interactively
intentspec init --quickstart

# Or convert an existing AGENTS.md
intentspec init --from AGENTS.md ./AGENTS.md

# Validate and score
intentspec validate
intentspec score

# Run all checks for CI/CD
intentspec ci --min-coverage 80
```

## Features

| Feature | Command | Description |
|---------|---------|-------------|
| **Validate** | `validate` | Schema + semantic validation of intent.yaml |
| **Score** | `score` | Intent Debt Score (IDS 0-100) with 7 weighted components |
| **Coverage** | `coverage` | Structural coverage analysis against source text |
| **Diff** | `diff` | Git-integrated intent change tracking between commits |
| **Lint** | `lint` | Quality checks (goal length, tool rationale, duplicates, etc.) |
| **CI** | `ci` | Unified hook: validate + lint + score + coverage in one pass |
| **Audit** | `audit-report` | SOC 2 / EU AI Act compliance report with SHA-256 hash |
| **Convert** | `init --from` | Import from AGENTS.md, SKILL.md, agentskills, CrewAI, LangGraph, AutoGen, OpenAI Agents |
| **Templates** | `init --template` | 5 built-in agent templates |
| **Health** | `health` | Terminal dashboard — coverage, IDS, stale/orphaned specs |
| **Drift** | `drift` | Detect stale intents (source file age vs last commit) |
| **Dashboard** | `dashboard --serve` | Web dashboard for coverage trends and IDS scores |

### New: Source Resolution

IntentSpec now resolves original agent source files (AGENTS.md, SKILL.md, framework configs) for any intent.yaml:

- `# Source:` header provenance (written by `intentspec init`)
- Sibling filename matching (AGENTS.md, SKILL.md, crewai.yaml, etc.)
- Orphaned spec detection (`health` and `drift` report specs with no source)

## Installation

```bash
pip install intentspec
```

Requires Python 3.11+.

## Why IntentSpec?

AI agents are defined by scattered markdown files, README comments, and tribal knowledge. IntentSpec makes that explicit and measurable:

1. **Document** — Define agent intent in a structured `intent.yaml`
2. **Convert** — Import existing AGENTS.md / SKILL.md / CrewAI specs
3. **Validate** — Schema + semantic checks catch misconfigurations
4. **Score** — Intent Debt Score (0-100) measures spec quality
5. **Coverage** — Compare intent against actual source text
6. **Enforce** — CI/CD integration fails builds when intent is missing or broken
7. **Audit** — Generate compliance reports for SOC 2 / EU AI Act

## License

MIT
