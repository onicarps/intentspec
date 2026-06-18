"""Additional emit tests covering list rendering and edge cases."""

from __future__ import annotations

import yaml

from intentspec.converter.emit import to_intent_yaml
from intentspec.converter.types import FieldSource, ParseResult
from intentspec.models.intent import (
    Boundary,
    Constraint,
    Goal,
    Intent,
    NonNegotiable,
    ToolPermission,
)


def _full_result() -> ParseResult:
    intent = Intent(
        agent_name="alpha",
        agent_type="coding",
        agent_description="Demo agent that uses lists.",
    )
    intent.goals.append(Goal(description="Build the foundation reliably.", priority="high"))
    intent.goals.append(Goal(description="Keep the API surface tiny.", priority="medium"))
    intent.constraints.append(Constraint(rule="NEVER push to main", enforceable=True))
    intent.constraints.append(Constraint(rule="prefer kebab-case names", enforceable=False))
    intent.non_negotiables.append(NonNegotiable(rule="Never log secrets", severity="hard"))
    intent.tools_allowed.append(ToolPermission(name="git", rationale="version control"))
    intent.tools_allowed.append(ToolPermission(name="pytest", rationale="run tests"))
    intent.boundaries.append(Boundary(scope="back-end services", out_of_scope="frontend UI"))

    confidences = {
        "agent.name": 0.85,
        "agent.type": 0.65,
        "agent.description": 0.50,
        "intent.goals[0].description": 0.80,
        "intent.constraints[0].rule": 0.85,
        "intent.tools.allowed[0].name": 0.75,
        "intent.boundaries[0].scope": 0.60,
    }
    sources = {
        "agent.name": FieldSource(line=1, snippet="# Alpha", extractor="rule"),
        "intent.goals[0].description": FieldSource(line=12, extractor="rule"),
        "intent.constraints[0].rule": FieldSource(line=25, extractor="rule"),
        "intent.tools.allowed[0].name": FieldSource(line=40, extractor="rule"),
    }
    return ParseResult(
        intent=intent,
        confidences=confidences,
        sources=sources,
        warnings=[],
        format="agents_md",
    )


def test_emit_full_intent_round_trip():
    result = _full_result()
    text = to_intent_yaml(result, "AGENTS.md")
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    data = yaml.safe_load(body)
    assert data["intent"]["goals"][0]["description"] == "Build the foundation reliably."
    assert data["intent"]["constraints"][0]["enforceable"] is True
    assert data["intent"]["constraints"][1]["enforceable"] is False
    assert data["intent"]["tools"]["allowed"][0]["name"] == "git"
    assert data["intent"]["boundaries"][0]["scope"] == "back-end services"


def test_emit_lists_per_entry_comments():
    result = _full_result()
    text = to_intent_yaml(result, "AGENTS.md")
    matched = [line for line in text.splitlines() if line.lstrip().startswith("- description:")]
    assert any("0.80" in line for line in matched)


def test_emit_long_snippet_truncated_in_comment():
    intent = Intent(agent_name="x", agent_type="custom", agent_description="d")
    long = "a" * 200
    pr = ParseResult(
        intent=intent,
        confidences={"agent.name": 0.5},
        sources={"agent.name": FieldSource(line=2, snippet=long, extractor="rule")},
        format="agents_md",
    )
    text = to_intent_yaml(pr, "x.md")
    line = next(ln for ln in text.splitlines() if "name:" in ln and "agent" not in ln.split(":")[0])
    assert "..." in line


def test_emit_handles_special_characters_in_strings():
    intent = Intent(
        agent_name="weird",
        agent_type="custom",
        agent_description="Has: colons, # hashes, and 'quotes'.",
    )
    pr = ParseResult(intent=intent, format="agents_md")
    text = to_intent_yaml(pr, "x.md")
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    data = yaml.safe_load(body)
    assert data["agent"]["description"] == "Has: colons, # hashes, and 'quotes'."
