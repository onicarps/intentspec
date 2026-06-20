# Schema Reference

Complete reference for the `intent.yaml` v1 schema.

## Full Schema

```yaml
version: "1.0"

agent:
  name: "my-agent"                 # Required. kebab-case identifier.
  type: "coding"                    # Required. See agent types below.
  description: "What this agent does" # Required. ≤200 chars.

intent:
  goals:
    - description: "What the agent achieves"  # Required.
      priority: "high"                        # high | medium | low
      success_criteria: "How to measure this" # Optional.

  constraints:
    - rule: "A rule the agent must follow"    # Required.
      enforceable: true                        # Required. true=auto-checkable, false=human-judgment.

  non_negotiables:
    - rule: "A hard boundary"                # Required.
      severity: "hard"                         # Required. hard=fail CI, soft=warn CI.

  tools:
    allowed:
      - name: "github_api"                    # Required.
        rationale: "Required for PR review"   # Required. WHY this tool.
    denied:
      - name: "production_deployer"           # Required.
        rationale: "Deployment requires human approval"  # Required.

  boundaries:
    - scope: "What's in scope"               # Required.
      out_of_scope: "What's explicitly out"  # Required.

  escalation:
    trigger: "When to escalate"              # Required.
    method: "How (human review, supervisor)"  # Optional.

  failure_modes:
    - mode: "Known failure mode"             # Required.
      mitigation: "How to prevent/handle"     # Required.

metadata:
  status: "draft"           # draft | active | deprecated
  owner: "team@company.com" # Responsible team or individual.
  created: "2026-01-01"     # ISO-8601 date.
  updated: "2026-01-15"     # ISO-8601 date.
  review_cycle: "monthly"   # e.g., "monthly", "quarterly"
  tags: ["coding", "review"] # Free-form tags.
```

## Agent Types

| Type | Description | Example |
|------|-------------|---------|
| `coding` | Code review and development | PR reviewer, code writer |
| `research` | Information gathering and analysis | Research assistant |
| `service` | User-facing service delivery | Customer support bot |
| `data` | Data pipelines and ETL | Data pipeline agent |
| `coordinator` | Multi-agent orchestration | Task planner, delegator |
| `custom` | User-defined | Anything else |

## Severity Levels

| Level | Behavior |
|-------|----------|
| `hard` | CI/CD pipeline fails (exit code 1) |
| `soft` | CI/CD pipeline warns (exit code 2) |

## Field Requirements

### Always Required
- `version` — Must be "1.0"
- `agent.name` — kebab-case identifier
- `agent.type` — One of the 6 agent types
- `agent.description` — ≤200 characters
- `intent` — Empty object `{}` is valid

### Conditionally Required (when parent is present)

| Parent Field | Required Child Fields |
|--------------|----------------------|
| `intent.goals[]` | `description`, `priority` |
| `intent.constraints[]` | `rule`, `enforceable` |
| `intent.non_negotiables[]` | `rule`, `severity` |
| `intent.tools.allowed[]` | `name`, `rationale` |
| `intent.tools.denied[]` | `name`, `rationale` |
| `intent.boundaries[]` | `scope`, `out_of_scope` |
| `intent.escalation` | `trigger` |
| `intent.failure_modes[]` | `mode`, `mitigation` |

### Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| `intent.goals[].success_criteria` | `""` | How to measure goal success |
| `intent.escalation.method` | `""` | How to escalate |
| `metadata.status` | `"draft"` | Lifecycle status |
| `metadata.owner` | `""` | Responsible party |
| `metadata.created` | `""` | Creation date |
| `metadata.updated` | `""` | Update date |
| `metadata.review_cycle` | `"monthly"` | Review frequency |
| `metadata.tags` | `[]` | Free-form labels |

## Validation Rules

Beyond schema structure, IntentSpec performs semantic validation:

| Rule | Severity |
|------|----------|
| Agent description should be > 10 characters | Warning |
| Goals should have descriptions > 10 characters | Warning |
| Tools should have rationale | Warning |
| Non-negotiables should have severity | Warning |
| No duplicate tool names in allowed or denied | Info |
| Tool names should not overlap between allowed and denied | Warning |

## Examples

### Minimal Valid Spec

```yaml
version: "1.0"
agent:
  name: "my-agent"
  type: "custom"
  description: "A simple agent"
intent: {}
```

### Full Featured Spec

See [Examples](examples.md) for complete real-world examples.
