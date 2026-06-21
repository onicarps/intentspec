# IntentSpec: Test Coverage for AI Agent Behavior

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

Import from any major agent spec format:

```bash
intentspec init --from AGENTS.md ./AGENTS.md
intentspec init --from crewai.yaml ./my-crew.yaml
intentspec init --from langgraph.yaml ./my-graph.yaml
```

Auto-detects format from file content. Supports AGENTS.md, SKILL.md, agentskills, CrewAI, LangGraph, AutoGen, and OpenAI Agents SDK.

### 2. Validate

Schema + semantic checks catch misconfigurations:

```
$ intentspec validate intent.yaml
  ✓ intent.yaml: valid
```

Validates against JSON Schema v1 plus semantic rules: goal description length, constraint enforceability, tool rationale, non-negotiable severity, duplicate tools, agent description quality.

### 3. Score

Intent Debt Score (0-100) measures spec quality across 7 weighted components:

```
$ intentspec score intent.yaml
  IDS Score: 96.0/100
    tool_coverage: 1.00
    goal_coverage: 1.00
    constraint_cov: 0.67
    non_negot_cov: 1.00
    freshness: 0.93
    completeness: 1.00
    consistency: 1.00
```

| Component | Weight | Measures |
|-----------|--------|----------|
| Tool coverage | 25% | Allowed tools with rationale |
| Goal coverage | 15% | Goals with meaningful descriptions |
| Completeness | 15% | 8 key fields populated |
| Non-negotiable coverage | 15% | Hard boundaries with severity |
| Constraint coverage | 10% | Enforceable constraints |
| Freshness | 10% | How recently updated |
| Consistency | 10% | No tool in both allowed and denied |

Higher score = better documented. 100 = fully documented, 0 = empty spec.

### 4. Enforce in CI/CD

Single command runs validate + lint + score + coverage:

```bash
intentspec ci --min-coverage 80 --strict
```

Exit codes: 0 = pass, 1 = validation error, 2 = warning, 3 = below threshold.

GitHub Action:

```yaml
- uses: onicarps/intentspec-action@v1
  with:
    min-coverage: 80
    strict: true
```

### 5. Track Changes

Git-integrated diff shows what changed in your agent's intent:

```bash
intentspec diff intent.yaml
intentspec diff --source-commit abc1234
```

### 6. Monitor Health

Terminal dashboard shows coverage trends, stale intents, and IDS distribution:

```bash
intentspec health
```

Web dashboard with Chart.js charts:

```bash
intentspec dashboard --serve --port 8080
```

### 7. Detect Drift

Find specs that haven't been updated in 30+ days:

```bash
intentspec drift --threshold-days 30
```

### 8. Audit & Compliance

Generate compliance reports for SOC 2 / EU AI Act:

```bash
intentspec audit-report intent.yaml --format json
```

Includes agent inventory, full spec dump, IDS score, SHA-256 hash, and generation timestamp.

## Sample intent.yaml

```yaml
version: "1.0"
agent:
  name: "code-reviewer"
  type: "coding"
  description: "Reviews PRs for code quality and security"
intent:
  goals:
    - description: "Identify bugs and security vulnerabilities"
      priority: "high"
    - description: "Enforce project style guide"
      priority: "medium"
  constraints:
    - rule: "Never approve PRs marked WIP"
      enforceable: true
    - rule: "Follow project style guide"
      enforceable: false
  non_negotiables:
    - rule: "Never approve code with hardcoded secrets"
      severity: "hard"
  tools:
    allowed:
      - name: "github_api"
        rationale: "Required for PR review and approval"
    denied:
      - name: "production_deployer"
        rationale: "Deployment requires human approval"
  boundaries:
    - scope: "Code review and development tasks"
      out_of_scope: "Production deployments, database migrations"
  escalation:
    trigger: "Security vulnerability with CVSS >= 7.0"
    method: "Page on-call engineer via Slack #security-team"
  failure_modes:
    - mode: "Approves code with subtle logic bugs"
      mitigation: "Require human sampling of approvals"
metadata:
  status: "active"
  owner: "team@company.com"
  review_cycle: "monthly"
  tags: ["coding", "review", "security"]
```

## Supported Formats

| Format | Auto-detect | Converter |
|--------|-------------|-----------|
| AGENTS.md | ✅ | `init --from AGENTS.md` |
| SKILL.md | ✅ | `init --from SKILL.md` |
| agentskills | ✅ | `init --from agentskills` |
| CrewAI | ✅ (filename) | `init --from crewai` |
| LangGraph | ✅ (filename) | `init --from langgraph` |
| AutoGen | ✅ (filename) | `init --from autogen` |
| OpenAI Agents | ✅ (filename) | `init --from openai_agents` |
| Templates | N/A | `init --template <name>` |

## Quickstart

```bash
# Create a new spec interactively (4 questions: name, type, non-negotiables, tools)
intentspec init --quickstart

# Or convert an existing spec
intentspec init --from AGENTS.md ./AGENTS.md

# Validate and score
intentspec validate
intentspec score

# Run all checks for CI/CD
intentspec ci --min-coverage 80

# Generate compliance report
intentspec audit-report

# Check health dashboard
intentspec health

# Detect stale specs
intentspec drift
```

## Why IntentSpec?

- **Transparent:** Agent behavior documented as code, not prose
- **Measurable:** Intent Debt Score tracks spec quality over time
- **Enforceable:** CI/CD integration fails builds when intent is missing or broken
- **Auditable:** Generate compliance reports for SOC 2 / EU AI Act
- **Universal:** Works with all major agent spec formats

## Get Started

```bash
pip install intentspec
```

Requires Python 3.11+.

**GitHub:** https://github.com/onicarps/intentspec
**Docs:** https://github.com/onicarps/intentspec/tree/main/docs
**License:** MIT
