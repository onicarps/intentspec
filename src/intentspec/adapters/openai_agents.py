"""OpenAI Agents SDK adapter — parse openai-agents.yaml into intent.yaml format.

OpenAI Agents config format reference:
  agents:
    - name: str
      instructions: str | list[str]
      guardrails:
        input: list[str]
        output: list[str]
      tools: list[str | {name: str, config: dict}]
      handoffs: list[{to: str, condition: str}]
      metadata: dict
  workflow:
    name: str
    description: str
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
    NonNegotiable,
    ToolPermission,
)


def parse_openai_agents(path: Path | str) -> ParseResult:
    """Parse an OpenAI Agents SDK config file into a ParseResult.

    Extracts:
      - agents[*].name / instructions → agent name + goals
      - agents[*].guardrails → non_negotiables + constraints
      - agents[*].tools → tools.allowed
      - agents[*].handoffs → boundaries
      - workflow.name → agent name fallback

    Args:
        path: Path to an openai-agents.yaml or openai-agents.yml file.

    Returns:
        A ParseResult with the extracted Intent.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid YAML or missing required fields.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"OpenAI Agents config not found: {path}")

    with open(path, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at top level, got {type(data).__name__}")

    agents = data.get("agents", [])
    workflow = data.get("workflow", {})

    # Agent identity
    agent_name = _extract_agent_name(workflow, agents)
    agent_description = _build_agent_description(workflow, agents)

    # Goals from instructions
    goals: list[Goal] = []
    for i, agent in enumerate(agents):
        if not isinstance(agent, dict):
            continue
        goal_text = _instructions_to_text(agent.get("instructions", ""))
        if not goal_text:
            goal_text = f"Execute {agent.get('name', f'agent {i + 1}')}"
        goals.append(Goal(
            description=goal_text[:200],
            priority=_agent_priority(i),
            success_criteria="",
        ))

    if not goals:
        goals.append(Goal(
            description="Execute OpenAI Agents workflow",
            priority="high",
            success_criteria="",
        ))

    # Constraints from guardrails (input guardrails)
    constraints: list[Constraint] = []
    non_negotiables: list[NonNegotiable] = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        guardrails = agent.get("guardrails", {})
        if not isinstance(guardrails, dict):
            continue
        agent_name_field = agent.get("name", "agent")
        for guardrail in guardrails.get("input", []):
            constraints.append(Constraint(
                rule=f"[{agent_name_field}] input guardrail: {guardrail}"[:500],
                enforceable=True,
            ))
        for guardrail in guardrails.get("output", []):
            non_negotiables.append(NonNegotiable(
                rule=f"[{agent_name_field}] output guardrail: {guardrail}",
                severity="hard",
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

    # Boundaries from handoffs
    boundaries: list[Boundary] = []
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_name_field = agent.get("name", "agent")
        handoffs = agent.get("handoffs", [])
        if isinstance(handoffs, list):
            for handoff in handoffs:
                if isinstance(handoff, dict):
                    target = handoff.get("to", "unknown")
                    condition = handoff.get("condition", "")
                    scope = f"{agent_name_field} can hand off to {target}"
                    if condition:
                        scope += f" when {condition}"
                    boundaries.append(Boundary(
                        scope=scope,
                        out_of_scope=f"Execution beyond {agent_name_field} scope without handoff",
                    ))
        # If no handoffs, agent works within its own scope
        if not handoffs:
            boundaries.append(Boundary(
                scope=f"{agent_name_field} operates within defined instructions",
                out_of_scope="Actions outside agent instructions or without handoff authorization",
            ))

    # Escalation — generic for OpenAI Agents
    escalation = Escalation(
        trigger="Agent guardrail violation or handoff loop detected",
        method="Escalate to human operator or supervisor agent",
    )

    # Failure modes — generic OpenAI Agents risks
    failure_modes = [
        FailureMode(
            mode="Guardrail bypass or injection attack",
            mitigation="Enable input validation guardrails and output filtering",
        ),
        FailureMode(
            mode="Agent produces output violating output guardrails",
            mitigation="Enable output guardrails with strict enforcement",
        ),
        FailureMode(
            mode="Handoff loop between agents",
            mitigation="Set maximum handoff depth and circular handoff detection",
        ),
    ]

    intent = Intent(
        version="1.0",
        agent_name=agent_name,
        agent_type="custom",
        agent_description=agent_description[:200],
        goals=goals,
        constraints=constraints,
        non_negotiables=non_negotiables,
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
            tags=["openai-agents", "imported"],
        ),
    )

    warnings: list[str] = []
    if not agents:
        warnings.append("No agents found in OpenAI Agents config")

    return ParseResult(
        intent=intent,
        warnings=warnings,
        format="openai_agents",
    )


def _extract_agent_name(workflow: dict[str, Any], agents: list[dict]) -> str:
    """Extract agent name from workflow or first agent."""
    name = workflow.get("name", "")
    if not name and agents and isinstance(agents[0], dict):
        name = agents[0].get("name", "openai-agent")
    if not name:
        name = "openai-agent"
    return _kebab_case(name)


def _build_agent_description(workflow: dict[str, Any], agents: list[dict]) -> str:
    """Build agent description from workflow and first agent."""
    parts: list[str] = []

    workflow_desc = workflow.get("description", "")
    if workflow_desc:
        parts.append(workflow_desc)

    if agents and isinstance(agents[0], dict):
        instructions = agents[0].get("instructions", "")
        if instructions:
            first_sentence = _instructions_to_text(instructions).split(".")[0].strip()
            if first_sentence and first_sentence not in parts:
                parts.append(first_sentence)

    if len(agents) > 1:
        parts.append(f"OpenAI Agents workflow with {len(agents)} agents")

    return ". ".join(parts) if parts else "Agent imported from OpenAI Agents SDK config"


def _instructions_to_text(instructions: Any) -> str:
    """Convert instructions (str or list[str]) to a single text string."""
    if isinstance(instructions, str):
        return instructions
    if isinstance(instructions, list):
        parts = []
        for item in instructions:
            if isinstance(item, str):
                parts.append(item)
        return ". ".join(parts)
    return ""


def _agent_priority(index: int) -> str:
    """Determine priority for an agent's goal."""
    if index == 0:
        return "high"
    return "medium"


def _extract_tool_name(tool_entry: Any) -> str:
    """Extract tool name from various tool entry formats.

    OpenAI Agents tools can be:
      - str: "tool_name"
      - dict: {"name": "tool_name", ...}
    """
    if isinstance(tool_entry, str):
        return tool_entry
    if isinstance(tool_entry, dict):
        name = tool_entry.get("name", "")
        if name:
            return name
    return ""


def _kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return "openai-agent"
    if not text[0].isalpha():
        text = "x-" + text
    return text[:64]
