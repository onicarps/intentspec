"""AutoGen adapter — parse autogen-config.yaml into intent.yaml format.

AutoGen config format reference:
  agents:
    - name: str
      system_message: str
      description: str
      tools: [str]
      model: str
      human_input_mode: str
      max_consecutive_auto_reply: int
  model_config:
    model: str
    temperature: float
  metadata:
    name: str
    description: str
    version: str
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from intentspec.converter.types import ParseResult
from intentspec.models.intent import (
    AgentMetadata,
    Boundary,
    Constraint,
    Escalation,
    FailureMode,
    Goal,
    Intent,
    ToolPermission,
)


def parse_autogen(path: Path | str) -> ParseResult:
    """Parse an AutoGen config file into a ParseResult.

    Extracts:
      - agents[*].name / description → agent name + description
      - agents[*].description → goals
      - agents[*].system_message → constraints
      - agents[*].tools → tools.allowed
      - metadata.name → agent name fallback

    Args:
        path: Path to an autogen-config.yaml or autogen-config.yml file.

    Returns:
        A ParseResult with the extracted Intent.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid YAML or missing required fields.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"AutoGen config not found: {path}")

    with open(path, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at top level, got {type(data).__name__}")

    metadata = data.get("metadata", {})
    agents = data.get("agents", [])

    # Agent identity — prefer metadata.name, fall back to first agent name
    agent_name = _extract_agent_name(metadata, agents)
    agent_description = _build_agent_description(metadata, agents)

    # Goals from agent descriptions
    goals: list[Goal] = []
    for i, agent in enumerate(agents):
        if not isinstance(agent, dict):
            continue
        goal_text = (
            agent.get("description")
            or agent.get("system_message")
            or f"Execute {agent.get('name', f'agent {i + 1}')}"
        )
        # Truncate long system messages for goal description
        if len(goal_text) > 200:
            goal_text = goal_text[:197] + "..."
        goals.append(Goal(
            description=goal_text,
            priority=_agent_priority(agent, i),
            success_criteria="",
        ))

    if not goals:
        goals.append(Goal(
            description="Execute AutoGen workflow",
            priority="high",
            success_criteria="",
        ))

    # Constraints from system_message fields
    constraints: list[Constraint] = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        system_message = agent.get("system_message", "")
        if system_message:
            agent_name_field = agent.get("name", "agent")
            # Extract first sentence as constraint
            first_sentence = system_message.split(".")[0].strip()
            if first_sentence:
                rule = f"Agent '{agent_name_field}' system instruction: {first_sentence}"
                constraints.append(Constraint(
                    rule=rule[:500],
                    enforceable=False,
                ))

    # Tools from agents
    tools_allowed: list[ToolPermission] = []
    seen_tools: set[str] = set()
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_name_field = agent.get("name", "unknown")
        for tool_entry in agent.get("tools", []):
            tool_name = _extract_tool_name(tool_entry)
            if tool_name and tool_name not in seen_tools:
                seen_tools.add(tool_name)
                tools_allowed.append(ToolPermission(
                    name=tool_name,
                    rationale=f"Used by agent: {agent_name_field}",
                ))

    # Boundaries from human_input_mode
    boundaries: list[Boundary] = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_name_field = agent.get("name", "agent")
        human_input = agent.get("human_input_mode", "NEVER")
        if human_input == "ALWAYS":
            boundaries.append(Boundary(
                scope=f"{agent_name_field} requires human input for every action",
                out_of_scope="Autonomous operation without human approval",
            ))
        elif human_input == "TERMINATE":
            boundaries.append(Boundary(
                scope=f"{agent_name_field} operates autonomously until termination condition",
                out_of_scope="Continuous operation beyond termination trigger",
            ))
        else:  # NEVER or default
            boundaries.append(Boundary(
                scope=f"{agent_name_field} operates autonomously",
                out_of_scope="Human-in-the-loop intervention during execution",
            ))

    # Escalation — generic for AutoGen
    escalation = Escalation(
        trigger="Agent conversation exceeds max rounds or produces invalid output",
        method="Escalate to AutoGen supervisor or human operator",
    )

    # Failure modes — generic AutoGen risks
    failure_modes = [
        FailureMode(
            mode="Agent conversation enters infinite loop",
            mitigation="Set max_consecutive_auto_reply and enable AutoGen termination conditions",
        ),
        FailureMode(
            mode="Agent produces hallucinated or incorrect output",
            mitigation="Enable AutoGen validation and human-in-the-loop review",
        ),
        FailureMode(
            mode="Multi-agent coordination failure",
            mitigation="Use AutoGen GroupChat with clear speaker selection rules",
        ),
    ]

    intent = Intent(
        version="1.0",
        agent_name=agent_name,
        agent_type="custom",
        agent_description=agent_description[:200],
        goals=goals,
        constraints=constraints,
        non_negotiables=[],
        tools_allowed=tools_allowed,
        tools_denied=[],
        boundaries=boundaries,
        escalation=escalation,
        failure_modes=failure_modes,
        metadata=AgentMetadata(
            status="draft",
            owner="",
            created="",
            updated="",
            review_cycle="monthly",
            tags=["autogen", "imported"],
        ),
    )

    warnings: list[str] = []
    if not agents:
        warnings.append("No agents found in AutoGen config")

    return ParseResult(
        intent=intent,
        warnings=warnings,
        format="autogen",
    )


def _extract_agent_name(metadata: dict[str, Any], agents: list[dict]) -> str:
    """Extract agent name from metadata or first agent."""
    name = metadata.get("name", "")
    if not name and agents and isinstance(agents[0], dict):
        name = agents[0].get("name", "autogen-agent")
    if not name:
        name = "autogen-agent"
    return _kebab_case(name)


def _build_agent_description(metadata: dict[str, Any], agents: list[dict]) -> str:
    """Build agent description from metadata and first agent."""
    parts: list[str] = []

    meta_desc = metadata.get("description", "")
    if meta_desc:
        parts.append(meta_desc)

    if agents and isinstance(agents[0], dict):
        agent_desc = agents[0].get("description", "")
        if agent_desc and agent_desc not in parts:
            parts.append(agent_desc)
        elif agents[0].get("system_message"):
            first_sentence = agents[0]["system_message"].split(".")[0].strip()
            if first_sentence and first_sentence not in parts:
                parts.append(first_sentence)

    if len(agents) > 1:
        parts.append(f"AutoGen multi-agent system with {len(agents)} agents")

    return ". ".join(parts) if parts else "Agent imported from AutoGen config"


def _agent_priority(agent: dict[str, Any], index: int) -> str:
    """Determine priority for an agent's goal."""
    explicit = agent.get("priority", "")
    if explicit in ("high", "medium", "low"):
        return explicit
    # First agent is high priority
    if index == 0:
        return "high"
    return "medium"


def _extract_tool_name(tool_entry: Any) -> str:
    """Extract tool name from various tool entry formats.

    AutoGen tools can be:
      - str: "tool_name"
      - dict: {"name": "tool_name", ...}
      - dict: {"type": "function", "function": {"name": "tool_name"}}
    """
    if isinstance(tool_entry, str):
        return tool_entry
    if isinstance(tool_entry, dict):
        name = tool_entry.get("name", "")
        if name:
            return name
        # OpenAI function format
        func = tool_entry.get("function", {})
        if isinstance(func, dict):
            return func.get("name", "")
    return ""


def _kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return "autogen-agent"
    if not text[0].isalpha():
        text = "x-" + text
    return text[:64]
