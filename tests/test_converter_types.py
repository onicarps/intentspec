"""Tests for converter/types.py — ParseResult and FieldSource dataclasses."""

from __future__ import annotations

import pytest

from intentspec.converter.types import ConverterError, FieldSource, ParseResult
from intentspec.models.intent import Intent


def test_field_source_defaults():
    fs = FieldSource()
    assert fs.line is None
    assert fs.snippet == ""
    assert fs.extractor == "rule"


def test_field_source_to_dict_round_trip():
    fs = FieldSource(line=42, snippet="hello", extractor="llm")
    d = fs.to_dict()
    assert d == {"line": 42, "snippet": "hello", "extractor": "llm"}
    fs2 = FieldSource.from_dict(d)
    assert fs2 == fs


def test_field_source_from_dict_with_missing_keys():
    fs = FieldSource.from_dict({"snippet": "x"})
    assert fs.line is None
    assert fs.snippet == "x"
    assert fs.extractor == "rule"


def test_parse_result_defaults():
    intent = Intent()
    intent.agent_name = "x"
    pr = ParseResult(intent=intent)
    assert pr.confidences == {}
    assert pr.sources == {}
    assert pr.warnings == []
    assert pr.format == ""


def test_parse_result_average_confidence_empty_returns_zero():
    pr = ParseResult(intent=Intent(), confidences={})
    assert pr.average_confidence() == 0.0


def test_parse_result_average_confidence_with_values():
    pr = ParseResult(
        intent=Intent(),
        confidences={"agent.name": 0.8, "agent.description": 0.4},
    )
    assert pr.average_confidence() == pytest.approx(0.6)


def test_parse_result_low_confidence_keys_below_threshold():
    pr = ParseResult(
        intent=Intent(),
        confidences={"a": 0.10, "b": 0.50, "c": 0.39},
    )
    assert pr.low_confidence_keys() == ["a", "c"]


def test_parse_result_to_serializable_keys():
    intent = Intent(agent_name="alpha", agent_type="coding", agent_description="desc")
    pr = ParseResult(
        intent=intent,
        confidences={"agent.name": 0.85},
        sources={"agent.name": FieldSource(line=1, snippet="# H", extractor="rule")},
        warnings=["w1"],
        format="agents_md",
    )
    payload = pr.to_serializable()
    assert set(payload.keys()) == {"intent", "confidences", "sources", "warnings", "format"}
    assert payload["format"] == "agents_md"
    assert payload["confidences"] == {"agent.name": 0.85}
    assert payload["sources"]["agent.name"]["line"] == 1
    assert payload["warnings"] == ["w1"]


def test_parse_result_to_serializable_sorts_keys():
    pr = ParseResult(
        intent=Intent(),
        confidences={"z": 0.1, "a": 0.2},
        sources={"z": FieldSource(), "a": FieldSource()},
    )
    payload = pr.to_serializable()
    assert list(payload["confidences"].keys()) == ["a", "z"]
    assert list(payload["sources"].keys()) == ["a", "z"]


def test_converter_error_is_exception():
    with pytest.raises(ConverterError):
        raise ConverterError("bad input")
