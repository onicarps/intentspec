# IntentSpec

**Coverage and enforcement layer for AI agent infrastructure.**

IntentSpec transforms agent development from ad-hoc documentation to versioned, testable, and enforceable intent. Document agent behavior as code, measure intent coverage, score intent debt, and enforce intent through CI/CD.

## Quickstart

```bash
pip install intentspec
intentspec init --quickstart
intentspec validate
```

## Features

- **Validate** — Schema + semantic validation of intent.yaml
- **Score** — Intent Debt Score (IDS 0-100) with 7 weighted components
- **Coverage** — Structural coverage analysis (tools, goals, constraints, non-negotiables)
- **Diff** — Git-integrated intent change tracking
- **Lint** — Quality checks for agent specs
- **CI** — Unified CI/CD hook with exit codes
- **Audit Report** — SOC 2 / EU AI Act compliance documents
- **Convert** — Import from AGENTS.md, SKILL.md, agentskills, CrewAI
- **Templates** — 5 built-in agent templates

## Supported Input Formats

| Format | Command |
|--------|---------|
| AGENTS.md | `intentspec init --from AGENTS.md <path>` |
| SKILL.md | `intentspec init --from SKILL.md <path>` |
| agentskills | `intentspec init --from agentskills <path>` |
| CrewAI | `intentspec init --from crewai.yaml <path>` |
| Templates | `intentspec init --template <name>` |

## License

MIT
