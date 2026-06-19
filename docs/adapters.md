# Adapters

IntentSpec can import agent specs from multiple formats.

## CrewAI

Parse a CrewAI `crewai.yaml` config into intent.yaml:

```bash
intentspec init --from crewai.yaml ./crewai.yaml
```

### Mapping

| CrewAI Field | intent.yaml Field |
|---------------|-------------------|
| `agents[].role` | `agent.name` (kebab-case) |
| `agents[].backstory` | `agent.description` |
| `agents[].tools` | `tools.allowed` |
| `agents[].allow_delegation` | `boundaries` |
| `tasks[].goal` | `intent.goals[].description` |
| `tasks[].description` | `intent.goals[].description` (fallback) |

### Example crewai.yaml

```yaml
agents:
  - role: "Researcher"
    backstory: "An expert researcher who finds and synthesizes information."
    allow_delegation: false
    tools:
      - "web_search"
      - "file_reader"

tasks:
  - description: "Research the topic"
    goal: "Find and synthesize relevant information"
```

## AGENTS.md

Parse an AGENTS.md file (Markdown with agent specification):

```bash
intentspec init --from AGENTS.md ./AGENTS.md
```

## SKILL.md

Parse a SKILL.md file (YAML frontmatter + Markdown body):

```bash
intentspec init --from SKILL.md ./SKILL.md
```

## agentskills

Parse an agentskills directory (SKILL.md + Resources/Scripts/References):

```bash
intentspec init --from agentskills ./my-skill/
```
