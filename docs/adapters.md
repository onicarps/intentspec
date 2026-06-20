# Adapters

IntentSpec can import agent specs from multiple formats. Each adapter extracts structured intent from the source format and produces a valid `intent.yaml`.

## Supported Formats

| Format | Command | Auto-detect |
|--------|---------|-------------|
| AGENTS.md | `init --from AGENTS.md <path>` | ✅ |
| SKILL.md | `init --from SKILL.md <path>` | ✅ |
| agentskills | `init --from agentskills <dir>` | ✅ |
| CrewAI | `init --from crewai.yaml <path>` | ✅ (filename) |
| LangGraph | `init --from langgraph.yaml <path>` | ✅ (filename) |
| AutoGen | `init --from autogen-config.yaml <path>` | ✅ (filename) |
| OpenAI Agents | `init --from openai-agents.yaml <path>` | ✅ (filename) |
| Templates | `init --template <name>` | N/A |

## AGENTS.md

Parses Markdown files with agent specifications. Extracts:
- Agent name and description from headings and body text
- Goals from "Goals", "Purpose", or "Responsibilities" sections
- Constraints from "Constraints", "Rules", or "Guidelines" sections
- Tools from "Tools" or "Capabilities" sections

```bash
intentspec init --from AGENTS.md ./AGENTS.md
```

## SKILL.md

Parses Markdown files with YAML frontmatter (YAML between `---` delimiters at the top). The frontmatter must contain a `name` key for auto-detection.

```bash
intentspec init --from SKILL.md ./my-skill/SKILL.md
```

## agentskills

Parses a directory containing `SKILL.md` plus optional `Resources/`, `Scripts/`, and `References/` subdirectories.

```bash
intentspec init --from agentskills ./my-skill-directory/
```

## CrewAI

Parses `crewai.yaml` or `crewai.yml` config files. Auto-detected by filename.

### Mapping

| CrewAI Field | intent.yaml Field |
|--------------|-------------------|
| `agents[].role` | `agent.name` (kebab-case) |
| `agents[].backstory` | `agent.description` |
| `agents[].tools` | `tools.allowed` |
| `agents[].allow_delegation` | `boundaries` |
| `tasks[].goal` | `intent.goals[].description` |
| `tasks[].description` | `intent.goals[].description` (fallback) |
| `tools[].name` | `tools.allowed` |

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

### Usage

```bash
# Auto-detect from filename
intentspec init --from crewai.yaml ./crewai.yaml

# Force format
intentspec init --from crewai ./my-config.yml --name my-agent
```

## Templates

Built-in templates for common agent types:

| Template | Type | Description |
|----------|------|-------------|
| `coding-agent` | coding | Code review and development |
| `research-agent` | research | Information gathering and analysis |
| `service-agent` | service | User-facing service delivery |
| `data-pipeline` | data | ETL and data quality |
| `multi-agent-coordinator` | coordinator | Multi-agent orchestration |

```bash
# List available templates
intentspec init --template list

# Use a template
intentspec init --template coding-agent --name my-reviewer
```

## Interactive Review

After conversion, IntentSpec runs an interactive review flow where you can:
- **Keep** (k) — Accept the extracted value as-is
- **Edit** (e) — Provide a new value
- **Drop** (d) — Remove the field
- **Finish** (f) — Accept all remaining fields and exit

```bash
intentspec init --from AGENTS.md ./AGENTS.md
#   Agent name [extracted-name]:
#   Agent description: An agent that...
#     Current: An agent that reviews code
#     Action [k/e/f]: e
#     New Agent description: A code review agent
```

Skip interactive mode with `--yes` or `--no-interactive`:

```bash
intentspec init --from AGENTS.md ./AGENTS.md --yes
```

## LLM Augmentation

Optionally augment rule-based extraction with an LLM for better accuracy:

```bash
intentspec init --from AGENTS.md ./AGENTS.md --use-llm
```

LLM extraction is opt-in and cached. Requires `OPENROUTER_API_KEY` environment variable.

## LangGraph

Parses LangGraph state graph configs. Extracts:
- Node descriptions → goals
- State schema fields → constraints
- Edges → boundaries
- Graph metadata → agent name

```bash
intentspec init --from langgraph.yaml ./langgraph.yaml
```

## AutoGen

Parses AutoGen agent configs. Extracts:
- Agent descriptions → goals
- System messages → constraints
- Agent tools → tools.allowed
- Human input mode → boundaries

```bash
intentspec init --from autogen-config.yaml ./autogen.yaml
```

## OpenAI Agents SDK

Parses OpenAI Agents SDK configs. Extracts:
- Agent instructions → goals
- Guardrails → constraints and non-negotiables
- Agent tools → tools.allowed
- Handoffs → boundaries

```bash
intentspec init --from openai-agents.yaml ./openai-agents.yaml
```
