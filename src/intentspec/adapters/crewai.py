"""CrewAI adapter — parse crewai.yaml into intent.yaml format.

CrewAI config format reference:
  agents:
    - role: str
      backstory: str
      allow_delegation: bool
      tools: [str]
  tasks:
    - description: str
      goal: str
  tools:
    - name: str
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from intentspec.converter.types import FieldSource, ParseResult
from intentspec.models.intent import (
    AgentMetadata,
    Boundary,
    Escalation,
    FailureMode,
    Goal,
    Intent,
    NonNegotiable,
    ToolPermission,
)


def parse_crewai(path: Path | str) -> ParseResult:
    """Parse a CrewAI config file into a ParseResult.

    Extracts:
      - agents[*].role / backstory → agent name + description
      - agents[*].tools → tools.allowed
      - agents[*].allow_delegation → boundaries
      - tasks[*].goal / description → goals

    Args:
        path: Path to a crewai.yaml or crewai.yml file.

    Returns:
        A ParseResult with the extracted Intent.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid YAML or missing required fields.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CrewAI config not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at top level, got {type(data).__name__}")

    agents = data.get("agents", [])
    tasks = data.get("tasks", [])
    tools_list = data.get("tools", [])

    # Agent identity — use first agent as primary
    if agents and isinstance(agents[0], dict):
        first_agent = agents[0]
        agent_name = _kebab_case(first_agent.get("role", "crewai-agent"))
        agent_description = _build_agent_description(first_agent, agents)
    else:
        agent_name = "crewai-agent"
        agent_description = "Agent imported from CrewAI config"

    # Goals from tasks
    goals: list[Goal] = []
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue
        goal_text = task.get("goal") or task.get("description") or f"Task {i + 1}"
        goals.append(Goal(
            description=goal_text,
            priority="medium",
            success_criteria="",
        ))

    if not goals:
        goals.append(Goal(
            description="Execute CrewAI workflow",
            priority="high",
            success_criteria="",
        ))

    # Tools from agents
    tools_allowed: list[ToolPermission] = []
    seen_tools: set[str] = set()
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        for tool_name in agent.get("tools", []):
            if isinstance(tool_name, str) and tool_name not in seen_tools:
                seen_tools.add(tool_name)
                tools_allowed.append(ToolPermission(
                    name=tool_name,
                    rationale=f"Used by agent: {agent.get('role', 'unknown')}",
                ))

    # Also check top-level tools
    for tool_entry in tools_list:
        if isinstance(tool_entry, dict):
            tool_name = tool_entry.get("name", "")
        elif isinstance(tool_entry, str):
            tool_name = tool_entry
        else:
            continue
        if tool_name and tool_name not in seen_tools:
            seen_tools.add(tool_name)
            tools_allowed.append(ToolPermission(
                name=tool_name,
                rationale="Declared in CrewAI tools",
            ))

    # Boundaries from allow_delegation
    boundaries: list[Boundary] = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        role = agent.get("role", "agent")
        if agent.get("allow_delegation"):
            boundaries.append(Boundary(
                scope=f"{role} can delegate to sub-agents",
                out_of_scope="Direct task execution without delegation chain",
            ))
        else:
            boundaries.append(Boundary(
                scope=f"{role} executes tasks directly",
                out_of_scope="Delegation to other agents",
            ))

    # Escalation — generic for CrewAI
    escalation = Escalation(
        trigger="Sub-agent task failure or timeout",
        method="Escalate to CrewAI supervisor or human operator",
    )

    # Failure modes — generic CrewAI risks
    failure_modes = [
        FailureMode(
            mode="Sub-agent produces incorrect output",
            mitigation="Enable CrewAI validation and human-in-the-loop review",
        ),
        FailureMode(
            mode="Delegation chain exceeds maximum depth",
            mitigation="Set max_delegation_depth in CrewAI config",
        ),
    ]

    intent = Intent(
        version="1.0",
        agent_name=agent_name,
        agent_type="custom",
        agent_description=agent_description[:200],
        goals=goals,
        constraints=[],
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
            tags=["crewai", "imported"],
        ),
    )

    warnings: list[str] = []
    if not agents:
        warnings.append("No agents found in CrewAI config")
    if not tasks:
        warnings.append("No tasks found in CrewAI config")

    return ParseResult(
        intent=intent,
        warnings=warnings,
        format="crewai",
    )


def _kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return "crewai-agent"
    if not text[0].isalpha():
        text = "x-" + text
    return text[:64]


def _build_agent_description(first_agent: dict[str, Any], all_agents: list[dict]) -> str:
    """Build a description from the first agent's role and backstory."""
    role = first_agent.get("role", "")
    backstory = first_agent.get("backstory", "")
    parts: list[str] = []
    if role:
        parts.append(role)
    if backstory:
        first_sentence = backstory.split(".")[0].strip()
        if first_sentence:
            parts.append(first_sentence)
    if len(all_agents) > 1:
        parts.append(f"Coordinator for {len(all_agents)} agents")
    return ". ".join(parts) if parts else "Agent imported from CrewAI config"
