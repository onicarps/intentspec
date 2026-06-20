"""LangGraph adapter — parse langgraph.yaml into intent.yaml format.

LangGraph config format reference:
  nodes:
    - name: str
      description: str
      type: str
      tools: [str]
      model: str
  edges:
    - from: str
      to: str
      condition: str
  state:
    schema:
      fields:
        - name: str
          type: str
          description: str
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
    Escalation,
    FailureMode,
    Goal,
    Intent,
    ToolPermission,
)


def parse_langgraph(path: Path | str) -> ParseResult:
    """Parse a LangGraph config file into a ParseResult.

    Extracts:
      - metadata.name / nodes[*].name → agent name
      - metadata.description / nodes[*].description → agent description
      - nodes[*].description → goals
      - nodes[*].tools → tools.allowed
      - state.schema.fields → constraints
      - edges → boundaries (graph connectivity)

    Args:
        path: Path to a langgraph.yaml or langgraph.yml file.

    Returns:
        A ParseResult with the extracted Intent.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid YAML or missing required fields.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"LangGraph config not found: {path}")

    with open(path, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at top level, got {type(data).__name__}")

    metadata = data.get("metadata", {})
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    state = data.get("state", {})

    # Agent identity — prefer metadata.name, fall back to first node
    agent_name = _extract_agent_name(metadata, nodes)
    agent_description = _build_agent_description(metadata, nodes)

    # Goals from node descriptions
    goals: list[Goal] = []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        goal_text = (
            node.get("description")
            or node.get("task")
            or f"Execute {node.get('name', f'node {i + 1}')}"
        )
        goals.append(Goal(
            description=goal_text,
            priority=_node_priority(node, i),
            success_criteria=node.get("success_criteria", ""),
        ))

    if not goals:
        goals.append(Goal(
            description="Execute LangGraph workflow",
            priority="high",
            success_criteria="",
        ))

    # Tools from nodes
    tools_allowed: list[ToolPermission] = []
    seen_tools: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_name = node.get("name", "unknown")
        for tool_name in node.get("tools", []):
            if isinstance(tool_name, str) and tool_name not in seen_tools:
                seen_tools.add(tool_name)
                tools_allowed.append(ToolPermission(
                    name=tool_name,
                    rationale=f"Used by node: {node_name}",
                ))

    # Constraints from state schema fields
    constraints = _extract_constraints(state)

    # Boundaries from edges
    boundaries: list[Boundary] = _extract_boundaries(edges, nodes)

    # Escalation — generic for LangGraph
    escalation = Escalation(
        trigger="Node execution failure or graph routing error",
        method="Escalate to LangGraph supervisor or human operator",
    )

    # Failure modes — generic LangGraph risks
    failure_modes = [
        FailureMode(
            mode="Node produces incorrect output",
            mitigation="Enable LangGraph validation nodes and human-in-the-loop review",
        ),
        FailureMode(
            mode="Graph routing enters infinite loop",
            mitigation="Set max_iterations and cycle detection in LangGraph config",
        ),
        FailureMode(
            mode="State schema mismatch between nodes",
            mitigation="Validate state schema with jsonschema before deployment",
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
            tags=["langgraph", "imported"],
        ),
    )

    warnings: list[str] = []
    if not nodes:
        warnings.append("No nodes found in LangGraph config")
    if not edges and len(nodes) > 1:
        warnings.append("Multiple nodes but no edges defined — graph may be disconnected")

    return ParseResult(
        intent=intent,
        warnings=warnings,
        format="langgraph",
    )


def _extract_agent_name(metadata: dict[str, Any], nodes: list[dict]) -> str:
    """Extract agent name from metadata or first node."""
    name = metadata.get("name", "")
    if not name and nodes and isinstance(nodes[0], dict):
        name = nodes[0].get("name", "langgraph-agent")
    if not name:
        name = "langgraph-agent"
    return _kebab_case(name)


def _build_agent_description(metadata: dict[str, Any], nodes: list[dict]) -> str:
    """Build agent description from metadata and first node."""
    parts: list[str] = []

    meta_desc = metadata.get("description", "")
    if meta_desc:
        parts.append(meta_desc)

    if nodes and isinstance(nodes[0], dict):
        node_desc = nodes[0].get("description", "")
        if node_desc and node_desc not in parts:
            parts.append(node_desc)

    if len(nodes) > 1:
        parts.append(f"LangGraph workflow with {len(nodes)} nodes")

    return ". ".join(parts) if parts else "Agent imported from LangGraph config"


def _node_priority(node: dict[str, Any], index: int) -> str:
    """Determine priority for a node's goal."""
    explicit = node.get("priority", "")
    if explicit in ("high", "medium", "low"):
        return explicit
    # First node is high priority
    if index == 0:
        return "high"
    return "medium"


def _extract_constraints(state: dict[str, Any]) -> list[Any]:
    """Extract constraints from state schema fields."""
    from intentspec.models.intent import Constraint

    constraints: list[Constraint] = []
    schema = state.get("schema", {})
    fields = schema.get("fields", [])

    for field in fields:
        if not isinstance(field, dict):
            continue
        field_name = field.get("name", "")
        field_type = field.get("type", "")
        field_desc = field.get("description", "")

        rule = f"State field '{field_name}' is required"
        if field_type:
            rule += f" (type: {field_type})"
        if field_desc:
            rule += f" — {field_desc}"

        constraints.append(Constraint(
            rule=rule,
            enforceable=True,
        ))

    return constraints


def _extract_boundaries(edges: list[dict], nodes: list[dict]) -> list[Any]:
    """Extract boundaries from graph edges."""
    from intentspec.models.intent import Boundary

    boundaries: list[Boundary] = []

    if not edges and len(nodes) <= 1:
        # Single node — no boundaries needed
        return boundaries

    # Build a set of connected nodes
    connected_nodes: set[str] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        from_node = edge.get("from", "")
        to_node = edge.get("to", "")
        if from_node:
            connected_nodes.add(from_node)
        if to_node:
            connected_nodes.add(to_node)

    # Identify isolated nodes
    all_node_names: set[str] = set()
    for node in nodes:
        if isinstance(node, dict) and node.get("name"):
            all_node_names.add(node["name"])

    isolated = all_node_names - connected_nodes
    if isolated:
        boundaries.append(Boundary(
            scope=f"Connected nodes: {', '.join(sorted(connected_nodes))}" if connected_nodes else "No connections",
            out_of_scope=f"Isolated nodes (no edges): {', '.join(sorted(isolated))}",
        ))

    if edges:
        boundaries.append(Boundary(
            scope=f"Graph has {len(edges)} edge(s) connecting {len(connected_nodes)} node(s)",
            out_of_scope="Direct node-to-node calls outside defined edges",
        ))

    return boundaries


def _kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return "langgraph-agent"
    if not text[0].isalpha():
        text = "x-" + text
    return text[:64]
