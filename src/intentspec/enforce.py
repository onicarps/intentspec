"""MCP intent enforcement — intent-first validation of MCP tool capabilities.

Validates MCP server tool capabilities against the agent intent spec
(what the agent SHOULD do), rather than just scanning permissions
(what the agent CAN do).
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPTool:
    """A tool exposed by an MCP server."""
    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnforcementResult:
    """Result of MCP intent enforcement."""
    server_tools: list[MCPTool] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    missing_from_spec: list[str] = field(default_factory=list)
    extra_in_spec: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    reachable: bool = True

    def to_text(self) -> str:
        lines = []
        if not self.reachable:
            lines.append("  WARNING: MCP server unreachable — results may be incomplete")
            return "\n".join(lines)

        lines.append(f"  Server tools: {len(self.server_tools)}")
        lines.append(f"  Intent spec tools: {len(self.allowed_tools)}")

        if self.missing_from_spec:
            lines.append(f"  Tools in server but NOT in intent spec ({len(self.missing_from_spec)}):")
            for t in self.missing_from_spec:
                lines.append(f"    - {t}")

        if self.extra_in_spec:
            lines.append(f"  Tools in intent spec but NOT in server ({len(self.extra_in_spec)}):")
            for t in self.extra_in_spec:
                lines.append(f"    - {t}")

        if self.risks:
            lines.append(f"  Risks ({len(self.risks)}):")
            for r in self.risks:
                lines.append(f"    ⚠ {r}")

        if not self.missing_from_spec and not self.extra_in_spec and not self.risks:
            lines.append("  ✓ All server tools are accounted for in intent spec")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "reachable": self.reachable,
            "server_tool_count": len(self.server_tools),
            "allowed_tool_count": len(self.allowed_tools),
            "missing_from_spec": self.missing_from_spec,
            "extra_in_spec": self.extra_in_spec,
            "risks": self.risks,
        }


def parse_mcp_config(config_path: str) -> dict[str, Any]:
    """Parse an MCP server configuration file.

    Supports JSON configs with a "servers" key containing server definitions.

    Args:
        config_path: Path to the MCP config file.

    Returns:
        Parsed config dict.

    Raises:
        ValueError: If config is malformed or missing required fields.
    """
    try:
        with open(config_path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Cannot read MCP config: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("MCP config must be a JSON object")

    return data


def discover_mcp_tools(server_config: dict[str, Any]) -> list[MCPTool]:
    """Discover tools from an MCP server configuration.

    In a real implementation, this would connect to the server via
    JSON-RPC and call tools/list. For now, parses tool definitions
    from the config file's "tools" array.

    Args:
        server_config: Server configuration dict.

    Returns:
        List of discovered tools.
    """
    tools = []
    raw_tools = server_config.get("tools", [])

    for raw in raw_tools:
        if isinstance(raw, str):
            tools.append(MCPTool(name=raw))
        elif isinstance(raw, dict):
            tools.append(MCPTool(
                name=raw.get("name", "unknown"),
                description=raw.get("description", ""),
                parameters=raw.get("inputSchema", raw.get("parameters", {})),
            ))

    return tools


def enforce_mcp(
    intent_allowed_tools: list[str],
    intent_denied_tools: list[str],
    server_tools: list[MCPTool],
) -> EnforcementResult:
    """Enforce intent spec against MCP server capabilities.

    Intent-first: validate that what the server exposes matches what
    the agent SHOULD do (declared in intent spec).

    Args:
        intent_allowed_tools: Tool names allowed by the intent spec.
        intent_denied_tools: Tool names denied by the intent spec.
        server_tools: Tools discovered on the MCP server.

    Returns:
        EnforcementResult with gaps and risks.
    """
    result = EnforcementResult(server_tools=server_tools)
    result.allowed_tools = intent_allowed_tools
    result.denied_tools = intent_denied_tools

    server_names = {t.name for t in server_tools}
    allowed_set = set(intent_allowed_tools)
    denied_set = set(intent_denied_tools)

    # Tools on server but not in intent spec
    result.missing_from_spec = sorted(server_names - allowed_set - denied_set)

    # Tools in intent spec but not on server
    result.extra_in_spec = sorted(allowed_set - server_names)

    # Risk: denied tools exist on server
    denied_on_server = denied_set & server_names
    if denied_on_server:
        result.risks.append(
            f"Denied tools exist on server: {sorted(denied_on_server)}"
        )

    # Risk: server has tools not declared anywhere
    undeclared = server_names - allowed_set - denied_set
    if undeclared:
        result.risks.append(
            f"Server exposes {len(undeclared)} tool(s) not declared in intent spec"
        )

    return result


def run_enforce(config_path: str | None = None,
                allowed_tools: list[str] | None = None,
                denied_tools: list[str] | None = None) -> EnforcementResult:
    """Run MCP enforcement from config or explicit tool lists.

    Args:
        config_path: Path to MCP server config JSON file.
        allowed_tools: Explicit list of allowed tools (if no config).
        denied_tools: Explicit list of denied tools (if no config).

    Returns:
        EnforcementResult.
    """
    if config_path:
        config = parse_mcp_config(config_path)
        # Support {"servers": {"name": {...}}} format
        servers = config.get("servers", {})
        if isinstance(servers, dict) and servers:
            server_name = next(iter(servers))
            server_cfg = servers[server_name]
        else:
            server_cfg = config
        tools = discover_mcp_tools(server_cfg)
    else:
        tools = []

    return enforce_mcp(
        allowed_tools or [],
        denied_tools or [],
        tools,
    )
