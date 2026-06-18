"""Tests for converter/emit.py — provenance header, comments, determinism."""

from __future__ import annotations

import json

import yaml

from intentspec.converter import parse, parse_quickstart
from intentspec.converter.emit import to_full_json, to_full_yaml, to_intent_yaml
from intentspec.converter.types import FieldSource, ParseResult
from intentspec.models.intent import Intent


def _make_result() -> ParseResult:
    intent = Intent(
        agent_name="my-agent",
        agent_type="coding",
        agent_description="A small agent for testing.",
    )
    return ParseResult(
        intent=intent,
        confidences={
            "agent.name": 0.85,
            "agent.type": 0.65,
            "agent.description": 0.30,
        },
        sources={
            "agent.name": FieldSource(line=1, snippet="# My Agent", extractor="rule"),
            "agent.type": FieldSource(extractor="default"),
            "agent.description": FieldSource(line=3, extractor="rule"),
        },
        warnings=["sample warning"],
        format="agents_md",
    )


def test_to_intent_yaml_starts_with_provenance_header():
    result = _make_result()
    text = to_intent_yaml(result, "AGENTS.md")
    head = text.splitlines()[:5]
    assert head[0].startswith("# intent.yaml")
    assert head[1].startswith("# Source: AGENTS.md")
    assert head[2].startswith("# Format: agents_md")
    assert head[3].startswith("# Confidence:")


def test_provenance_header_contains_required_substrings():
    result = _make_result()
    text = to_intent_yaml(result, "src.md")
    assert "Source:" in text
    assert "Format: agents_md" in text
    assert "Confidence:" in text


def test_per_field_comments_include_confidence_and_source():
    result = _make_result()
    text = to_intent_yaml(result, "src.md")
    for line in text.splitlines():
        if line.lstrip().startswith("name: my-agent"):
            assert "confidence:" in line
            assert "source:" in line
            assert "0.85" in line
            return
    raise AssertionError("agent.name line not found")


def test_emit_yaml_is_parseable():
    result = _make_result()
    text = to_intent_yaml(result, "src.md")
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    data = yaml.safe_load(body)
    assert data["agent"]["name"] == "my-agent"
    assert data["agent"]["type"] == "coding"


def test_emit_is_deterministic_byte_for_byte():
    result1 = _make_result()
    result2 = _make_result()
    a = to_intent_yaml(result1, "src.md")
    b = to_intent_yaml(result2, "src.md")
    assert a == b


def test_emit_uses_lf_line_endings():
    result = _make_result()
    text = to_intent_yaml(result, "src.md")
    assert "\r" not in text


def test_to_full_json_round_trips():
    result = _make_result()
    text = to_full_json(result, "src.md")
    payload = json.loads(text)
    assert set(payload.keys()) >= {"intent", "confidences", "sources", "warnings", "format"}
    assert payload["intent"]["agent"]["name"] == "my-agent"
    assert payload["confidences"]["agent.name"] == 0.85
    assert payload["sources"]["agent.name"]["extractor"] == "rule"
    assert payload["warnings"] == ["sample warning"]
    assert payload["format"] == "agents_md"


def test_to_full_yaml_round_trips():
    result = _make_result()
    text = to_full_yaml(result, "src.md")
    payload = yaml.safe_load(text)
    assert set(payload.keys()) >= {"intent", "confidences", "sources", "warnings", "format"}
    assert payload["intent"]["agent"]["name"] == "my-agent"


def test_emit_includes_warning_in_provenance():
    result = _make_result()
    text = to_intent_yaml(result, "src.md")
    assert "sample warning" in text


def test_emit_lists_low_confidence_fields_for_review():
    result = _make_result()
    text = to_intent_yaml(result, "src.md")
    review_line = next((l for l in text.splitlines() if "Fields requiring review" in l), None)
    assert review_line is not None
    assert "agent.description" in review_line


def test_emit_empty_intent_block_renders_inline_braces():
    result = parse_quickstart({"agent_name": "Demo", "agent_type": "custom", "agent_description": "test"})
    text = to_intent_yaml(result, "quickstart")
    assert "intent: {}" in text


def test_emit_round_trip_with_real_fixture(tmp_path):
    fixture = tmp_path / "AGENTS.md"
    fixture.write_text("# Demo Agent\nDoes things.\n", encoding="utf-8")
    result = parse(fixture)
    text = to_intent_yaml(result, str(fixture))
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    data = yaml.safe_load(body)
    assert data["version"] == "1.0"
    assert data["agent"]["name"]
    assert "intent" in data


def test_emit_includes_per_field_comment_for_all_populated_keys():
    result = _make_result()
    text = to_intent_yaml(result, "src.md")
    for path, conf in result.confidences.items():
        last_segment = path.split(".")[-1]
        matching = [l for l in text.splitlines() if l.lstrip().startswith(f"{last_segment}:")]
        assert any("confidence:" in line for line in matching), f"missing comment for {path}"
