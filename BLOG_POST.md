# IntentSpec: Test Coverage for Agent Behavior

**Published:** June 20, 2026
**Author:** oni
**Tags:** ai-agents, testing, open-source, cli

## The Problem

AI agents are defined by scattered markdown files, README comments, and tribal knowledge. AGENTS.md here, a SKILL.md there, a crewai.yaml somewhere else. There's no standard way to answer basic questions like:

- What is this agent supposed to do?
- What tools is it allowed to use?
- What are its hard boundaries?
- How complete is its specification?

## The Solution

IntentSpec transforms agent development from ad-hoc documentation to versioned, testable, and enforceable intent.

```bash
pip install intentspec
intentspec init --quickstart
intentspec validate
intentspec score
```

## What It Does

### 1. Convert Existing Specs → intent.yaml

Import from any format:

```bash
intentspec init --from AGENTS.md ./AGENTS.md
intentspec init --from crewai.yaml ./my-crew.yaml
intentspec init --from langgraph.yaml ./my-graph.yaml
```

### 2. Validate

Schema + semantic checks catch misconfigurations:

```
✓ intent.yaml: valid
  IDS Score: 96.0/100
```

### 3. Score

Intent Debt Score (0-100) measures spec quality across 7 weighted components:

| Component | Weight |
|-----------|--------|
| Tool coverage | 25% |
| Goal coverage | 15% |
| Completeness | 15% |
| Non-negotiable coverage | 15% |
| Constraint coverage | 10% |
| Freshness | 10% |
| Consistency | 10% |

### 4. Enforce in CI/CD

```yaml
- uses: onicarps/intentspec-action@v1
  with:
    min-coverage: 80
    strict: true
```

### 5. Detect Drift

```bash
intentspec health     # coverage trend, stale intents, IDS distribution
intentspec drift      # specs not updated in 30+ days
intentspec dashboard  # web UI with charts
```

## Supported Formats

| Format | Auto-detect | Converter |
|--------|-------------|-----------|
| AGENTS.md | ✅ | `init --from AGENTS.md` |
| SKILL.md | ✅ | `init --from SKILL.md` |
| agentskills | ✅ | `init --from agentskills` |
| CrewAI | ✅ (filename) | `init --from crewai.yaml` |
| LangGraph | ✅ (filename) | `init --from langgraph.yaml` |
| AutoGen | ✅ (filename) | `init --from autogen-config.yaml` |
| OpenAI Agents | ✅ (filename) | `init --from openai-agents.yaml` |

## Quickstart

```bash
# Create a new spec interactively
intentspec init --quickstart

# Validate and score
intentspec validate
intentspec score

# Run all checks for CI/CD
intentspec ci --min-coverage 80

# Generate compliance report
intentspec audit-report

# Check health dashboard
intentspec health
```

## Why IntentSpec?

- **Transparent:** Agent behavior documented as code, not prose
- **Measurable:** Intent Debt Score tracks spec quality over time
- **Enforceable:** CI/CD integration fails builds when intent is missing or broken
- **Auditable:** Generate compliance reports for SOC 2 / EU AI Act
- **Universal:** Works with any agent spec format

## Get Started

```bash
pip install intentspec
```

**GitHub:** https://github.com/onicarps/intentspec
**Docs:** https://intentspec.dev
**License:** MIT
