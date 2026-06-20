# Integration Guide

How IntentSpec integrates with other agent tools and frameworks.

## Eval Harness (lm-eval-harness)

IntentSpec intent specs can serve as evaluation dimensions for benchmarking LLMs.

### Integration Pattern

```python
# Use intent.yaml as eval dimensions
from intentspec.spec.validate import validate_file

intent, errors, warnings = validate_file("intent.yaml")

# Extract goals as evaluation criteria
for goal in intent.goals:
    print(f"Eval dimension: {goal.description}")
    print(f"Priority: {goal.priority}")
    if goal.success_criteria:
        print(f"Success criteria: {goal.success_criteria}")
```

### Use Cases

1. **Goal coverage evaluation** — Measure how well an agent's output covers the declared goals
2. **Constraint compliance** — Check if agent behavior respects declared constraints
3. **Tool usage auditing** — Verify only declared tools are used
4. **IDS as quality metric** — Track Intent Debt Score over time as a proxy for spec quality

### Cross-Reference

- [lm-eval-harness](https://github.com/EleutherAI/lm-evaluation-harness) — LLM evaluation framework
- IntentSpec `score` command provides IDS 0-100 that can be used as an eval dimension

## Agent-Guard

IntentSpec intent specs document the rationale for tool permissions, which can inform agent-guard policies.

### Integration Pattern

```yaml
# intent.yaml — documents WHY each tool is allowed/denied
intent:
  tools:
    allowed:
      - name: "github_api"
        rationale: "Required for PR review, commenting, approval"
    denied:
      - name: "production_deployer"
        rationale: "Deployment requires human approval"
```

### Use Cases

1. **Permission justification** — The `rationale` field documents why each tool is needed
2. **Audit trail** — `audit-report` generates compliance documents with tool justifications
3. **Policy generation** — Intent specs can be transformed into agent-guard policies

### Cross-Reference

- Agent-guard uses intent specs as a source of truth for "why does this agent have this tool?"
- IntentSpec `audit-report` generates SOC 2 / EU AI Act compliance documents that include tool rationales

## Framework Adapters

IntentSpec imports from multiple agent frameworks:

| Framework | Command | Status |
|-----------|---------|--------|
| AGENTS.md | `init --from AGENTS.md <path>` | ✅ |
| SKILL.md | `init --from SKILL.md <path>` | ✅ |
| agentskills | `init --from agentskills <dir>` | ✅ |
| CrewAI | `init --from crewai.yaml <path>` | ✅ |
| LangGraph | `init --from langgraph.yaml <path>` | ✅ |
| AutoGen | `init --from autogen-config.yaml <path>` | 🔄 |
| OpenAI Agents | `init --from openai-agents.yaml <path>` | 🔄 |
