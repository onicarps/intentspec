# IntentSpec

**Coverage and enforcement layer for AI agent infrastructure.**

[![PyPI](https://img.shields.io/pypi/v/intentspec)](https://pypi.org/project/intentspec/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/onicarps/intentspec/workflows/CI/badge.svg)](https://github.com/onicarps/intentspec/actions)

IntentSpec transforms agent development from ad-hoc documentation to versioned, testable, and enforceable intent. Document agent behavior as code, measure intent coverage, score intent debt, and enforce intent through CI/CD.

## Quickstart

```bash
pip install intentspec
intentspec init --quickstart
intentspec validate
intentspec score
```

## Features

- **Validate** — Schema + semantic validation of intent.yaml
- **Score** — Intent Debt Score (IDS 0-100) with 7 weighted components
- **Coverage** — Structural coverage analysis
- **Diff** — Git-integrated intent change tracking
- **Lint** — Quality checks for agent specs
- **CI** — Unified CI/CD hook with exit codes
- **Audit Report** — SOC 2 / EU AI Act compliance documents
- **Convert** — Import from AGENTS.md, SKILL.md, agentskills, CrewAI
- **Templates** — 5 built-in agent templates

## Installation

```bash
pip install intentspec
```

## Commands

| Command | Description |
|---------|-------------|
| `validate` | Validate intent.yaml against schema |
| `init` | Initialize from spec, template, or wizard |
| `score` | Calculate Intent Debt Score (IDS) |
| `coverage` | Show coverage percentage |
| `diff` | Show intent changes between commits |
| `lint` | Quality checks |
| `ci` | CI/CD hook (validate + lint + score + coverage) |
| `audit-report` | Generate compliance document |

## Config File

IntentSpec looks for `.intentspec.yaml` in the current directory:

```yaml
min_coverage: 80
strict: false
format: text
```

Config precedence: CLI flags > env vars > config file > defaults.

## License

MIT
