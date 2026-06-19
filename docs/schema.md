# Schema Reference

## intent.yaml v1.0

```yaml
version: "1.0"

agent:
  name: string                    # Required. kebab-case identifier.
  type: enum                       # Required. coding | research | service | data | coordinator | custom
  description: string              # Required. ≤200 chars.

intent:
  goals:                           # Optional.
    - description: string          # Required. What the agent achieves.
      priority: enum               # high | medium | low
      success_criteria: string     # Optional. How to measure this goal.

  constraints:                     # Optional.
    - rule: string                 # Required. The rule text.
      enforceable: boolean         # Required. true = auto-checkable, false = human judgment.

  non_negotiables:                 # Optional. Hard boundaries.
    - rule: string                 # Required.
      severity: enum               # hard = CI fail, soft = CI warning.

  tools:                           # Optional.
    allowed:                       # Tools the agent CAN use.
      - name: string               # Required.
        rationale: string          # Required. WHY this tool is needed.
    denied:                        # Tools the agent CANNOT use.
      - name: string               # Required.
        rationale: string          # Required. WHY this tool is forbidden.

  boundaries:                      # Optional.
    - scope: string                # What's in scope.
      out_of_scope: string         # What's explicitly out.

  escalation:                      # Optional.
    trigger: string                # When to escalate.
    method: string                 # How (human review, supervisor agent, etc.).

  failure_modes:                   # Optional. Known ways this agent can fail.
    - mode: string                 # Required.
      mitigation: string           # Required.

metadata:
  status: enum                     # draft | active | deprecated
  owner: string                    # Team or individual responsible.
  created: string                  # ISO-8601 date.
  updated: string                  # ISO-8601 date.
  review_cycle: string             # e.g., "monthly"
  tags: [string]                   # Free-form tags.
```

## Agent Types

| Type | Description |
|------|-------------|
| `coding` | Code review and development tasks |
| `research` | Information gathering and analysis |
| `service` | User-facing service delivery |
| `data` | Data pipelines and ETL |
| `coordinator` | Multi-agent orchestration |
| `custom` | User-defined agent type |

## Severity Levels

| Level | Behavior |
|-------|----------|
| `hard` | CI/CD pipeline fails |
| `soft` | CI/CD pipeline warns |
