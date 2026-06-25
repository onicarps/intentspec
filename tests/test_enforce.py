"""Tests for MCP intent enforcement."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from intentspec.enforce import (
    EnforcementResult,
    MCPTool,
    enforce_mcp,
    parse_mcp_config,
    run_enforce,
)


class TestEnforceMCP:
    def test_all_tools_accounted(self):
        result = enforce_mcp(
            intent_allowed_tools=["read", "write"],
            intent_denied_tools=["delete"],
            server_tools=[
                MCPTool(name="read"),
                MCPTool(name="write"),
            ],
        )
        assert result.missing_from_spec == []
        assert result.extra_in_spec == []
        assert result.risks == []

    def test_missing_from_spec(self):
        result = enforce_mcp(
            intent_allowed_tools=["read"],
            intent_denied_tools=[],
            server_tools=[
                MCPTool(name="read"),
                MCPTool(name="write"),
                MCPTool(name="delete"),
            ],
        )
        assert "write" in result.missing_from_spec
        assert "delete" in result.missing_from_spec

    def test_extra_in_spec(self):
        result = enforce_mcp(
            intent_allowed_tools=["read", "write", "admin"],
            intent_denied_tools=[],
            server_tools=[MCPTool(name="read")],
        )
        assert "write" in result.extra_in_spec
        assert "admin" in result.extra_in_spec

    def test_denied_on_server_risk(self):
        result = enforce_mcp(
            intent_allowed_tools=["read"],
            intent_denied_tools=["delete"],
            server_tools=[
                MCPTool(name="read"),
                MCPTool(name="delete"),
            ],
        )
        assert len(result.risks) == 1
        assert "delete" in result.risks[0]

    def test_undeclared_tools_risk(self):
        result = enforce_mcp(
            intent_allowed_tools=["read"],
            intent_denied_tools=[],
            server_tools=[
                MCPTool(name="read"),
                MCPTool(name="secret_tool"),
            ],
        )
        assert any("undeclared" in r.lower() or "not declared" in r.lower() for r in result.risks)


class TestParseMCPConfig:
    def test_parse_simple_config(self, tmp_path):
        config = {"tools": [{"name": "read"}, {"name": "write"}]}
        path = tmp_path / "mcp.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        result = parse_mcp_config(str(path))
        assert "tools" in result

    def test_parse_server_wrapper(self, tmp_path):
        config = {
            "servers": {
                "my-server": {
                    "command": "python",
                    "tools": [{"name": "read"}],
                }
            }
        }
        path = tmp_path / "mcp.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        result = parse_mcp_config(str(path))
        assert "servers" in result

    def test_malformed_file_raises(self, tmp_path):
        path = tmp_path / "mcp.json"
        path.write_text("not json", encoding="utf-8")
        with pytest.raises(ValueError, match="Cannot read"):
            parse_mcp_config(str(path))

    def test_missing_file_raises(self):
        with pytest.raises(ValueError, match="Cannot read"):
            parse_mcp_config("/nonexistent/mcp.json")


class TestRunEnforce:
    def test_with_config(self, tmp_path):
        config = {"tools": [{"name": "read"}, {"name": "write"}]}
        path = tmp_path / "mcp.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        result = run_enforce(config_path=str(path), allowed_tools=["read"], denied_tools=[])
        assert isinstance(result, EnforcementResult)
        assert len(result.server_tools) == 2

    def test_without_config(self):
        result = run_enforce(allowed_tools=["read"], denied_tools=[])
        assert result.reachable
        assert len(result.server_tools) == 0


class TestEnforcementResult:
    def test_to_text_clean(self):
        result = EnforcementResult()
        result.server_tools = [MCPTool(name="read")]
        result.allowed_tools = ["read"]
        text = result.to_text()
        assert "accounted for" in text

    def test_to_dict(self):
        result = EnforcementResult(reachable=True)
        result.server_tools = [MCPTool(name="read")]
        result.allowed_tools = ["read"]
        d = result.to_dict()
        assert d["reachable"] is True
        assert d["server_tool_count"] == 1
