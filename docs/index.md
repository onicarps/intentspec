# IntentSpec

**Coverage and enforcement layer for AI agent infrastructure.**

IntentSpec transforms agent development from ad-hoc documentation to versioned, testable, and enforceable intent. Document agent behavior as code, measure intent coverage, score intent debt, and enforce intent through CI/CD.

## Quickstart

```bash
pip install intentspec
intentspec init --quickstart
intentspec validate
intentspec score
intentspec ci
```

## What It Does

1. **Document** — Define agent intent in a structured `intent.yaml`
2. **Convert** — Import existing AGENTS.md / SKILL.md / CrewAI specs
3. **Validate** — Schema + semantic checks catch misconfigurations
4. **Score** — Intent Debt Score (0-100) measures spec quality
5. **Coverage** — Compare intent against actual source text
6. **Enforce** — CI/CD integration fails builds when intent is broken
7. **Audit** — Generate compliance reports for SOC 2 / EU AI Act

## Features

| Feature | Command | Description |
|---------|---------|-------------|
| Validate | `validate` | Schema + semantic validation |
| Score | `score` | Intent Debt Score (IDS 0-100) |
| Coverage | `coverage` | Structural coverage analysis |
| Diff | `diff` | Git-integrated change tracking |
| Lint | `lint` | Quality checks |
| CI | `ci` | Unified CI/CD hook |
| Audit | `audit-report` | Compliance report generation |
| Convert | `init --from` | Import from 4 source formats |
| Templates | `init --template` | 5 built-in agent templates |

## Input Formats

- **AGENTS.md** — Markdown with agent specification
- **SKILL.md** — Markdown with YAML frontmatter
- **agentskills** — Directory with SKILL.md + Resources/Scripts/References
- **CrewAI** — `crewai.yaml` config file
- **Templates** — Built-in templates for common agent types

## License

MIT

## Links

- **GitHub:** https://github.com/onicarps/intentspec
- **Issues:** https://github.com/onicarps/intentspec/issues
- **Linear:** IntentSpec project (ONI team) — issues ONI-156 to ONI-165
