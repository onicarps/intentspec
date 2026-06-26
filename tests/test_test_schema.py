"""Tests for intent-test.yaml schema + parser (test_schema.py)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from intentspec.test_schema import (
    IntentTest,
    IntentTestSchemaError,
    TestCase,
    parse_intent_test,
)


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "intent-test.yaml"
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


class TestValidParsing:
    def test_valid_file_parses_into_populated_dataclasses(self, tmp_path):
        # VAL-SCHEMA-001
        path = _write(tmp_path, """
            name: my-suite
            description: a full suite
            tests:
              - name: has-goals
                type: presence_check
                description: goals present
                field: goals
                severity: warning
              - name: name-format
                type: regex_check
                field: agent.name
                assert: "^[a-z][a-z0-9-]*$"
        """)
        result = parse_intent_test(path)
        assert isinstance(result, IntentTest)
        assert result.name == "my-suite"
        assert result.description == "a full suite"
        assert len(result.tests) == 2
        first = result.tests[0]
        assert isinstance(first, TestCase)
        assert first.name == "has-goals"
        assert first.type == "presence_check"
        assert first.description == "goals present"
        assert first.field == "goals"
        assert first.severity == "warning"
        assert first.assertion == ""
        second = result.tests[1]
        assert second.type == "regex_check"
        assert second.field == "agent.name"
        assert second.assertion == "^[a-z][a-z0-9-]*$"

    def test_all_five_types_parse(self, tmp_path):
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: c1
                type: constraint_check
                assert: "tools.denied intersect tools.allowed == empty"
              - name: p1
                type: presence_check
                field: escalation
              - name: n1
                type: count_check
                assert: "len(goals) > 0"
              - name: r1
                type: regex_check
                field: agent.name
                assert: "^[a-z]+$"
              - name: x1
                type: cross_reference
                assert: "every sub_agents subset goals"
        """)
        result = parse_intent_test(path)
        assert [tc.type for tc in result.tests] == [
            "constraint_check",
            "presence_check",
            "count_check",
            "regex_check",
            "cross_reference",
        ]


class TestFileErrors:
    def test_missing_file_raises_filenotfound(self, tmp_path):
        # VAL-SCHEMA-002
        with pytest.raises(FileNotFoundError):
            parse_intent_test(tmp_path / "nope.yaml")

    def test_empty_file_raises_schema_error(self, tmp_path):
        # VAL-SCHEMA-003
        path = _write(tmp_path, "")
        with pytest.raises(IntentTestSchemaError):
            parse_intent_test(path)

    def test_non_dict_top_level_raises_schema_error(self, tmp_path):
        # VAL-SCHEMA-003
        path = _write(tmp_path, """
            - just
            - a
            - list
        """)
        with pytest.raises(IntentTestSchemaError):
            parse_intent_test(path)

    def test_scalar_top_level_raises_schema_error(self, tmp_path):
        # VAL-SCHEMA-003
        path = _write(tmp_path, "just a scalar string\n")
        with pytest.raises(IntentTestSchemaError):
            parse_intent_test(path)


class TestTopLevelSchema:
    def test_missing_name_raises_naming_field(self, tmp_path):
        # VAL-SCHEMA-004
        path = _write(tmp_path, """
            description: no name here
            tests: []
        """)
        with pytest.raises(IntentTestSchemaError) as exc:
            parse_intent_test(path)
        assert any("name" in m for m in exc.value.errors)

    def test_absent_tests_yields_empty_list(self, tmp_path):
        # VAL-SCHEMA-005
        path = _write(tmp_path, """
            name: suite-without-tests
        """)
        result = parse_intent_test(path)
        assert result.tests == []

    def test_empty_tests_yields_empty_list(self, tmp_path):
        # VAL-SCHEMA-005
        path = _write(tmp_path, """
            name: suite
            tests: []
        """)
        result = parse_intent_test(path)
        assert result.tests == []

    def test_unknown_top_level_field_rejected(self, tmp_path):
        # VAL-SCHEMA-011
        path = _write(tmp_path, """
            name: suite
            descriptionn: typo here
            tests: []
        """)
        with pytest.raises(IntentTestSchemaError) as exc:
            parse_intent_test(path)
        assert any("descriptionn" in m for m in exc.value.errors)


class TestCaseSchema:
    def test_missing_case_name_identifies_test(self, tmp_path):
        # VAL-SCHEMA-006
        path = _write(tmp_path, """
            name: suite
            tests:
              - type: presence_check
                field: goals
        """)
        with pytest.raises(IntentTestSchemaError) as exc:
            parse_intent_test(path)
        joined = " ".join(exc.value.errors)
        assert "name" in joined

    def test_invalid_type_enum_raises(self, tmp_path):
        # VAL-SCHEMA-007
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: bad
                type: magic_check
                assert: "x"
        """)
        with pytest.raises(IntentTestSchemaError) as exc:
            parse_intent_test(path)
        assert any("magic_check" in m or "type" in m for m in exc.value.errors)

    @pytest.mark.parametrize("ttype", ["constraint_check", "count_check", "regex_check"])
    def test_assert_required_for_constraint_count_regex(self, tmp_path, ttype):
        # VAL-SCHEMA-008
        path = _write(tmp_path, f"""
            name: suite
            tests:
              - name: needs-assert
                type: {ttype}
        """)
        with pytest.raises(IntentTestSchemaError) as exc:
            parse_intent_test(path)
        assert any("assert" in m for m in exc.value.errors)

    def test_empty_assert_rejected_for_constraint(self, tmp_path):
        # VAL-SCHEMA-008
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: needs-assert
                type: constraint_check
                assert: ""
        """)
        with pytest.raises(IntentTestSchemaError) as exc:
            parse_intent_test(path)
        assert any("assert" in m for m in exc.value.errors)

    @pytest.mark.parametrize("ttype", ["presence_check", "cross_reference"])
    def test_assert_optional_for_presence_and_cross_reference(self, tmp_path, ttype):
        # VAL-SCHEMA-009
        path = _write(tmp_path, f"""
            name: suite
            tests:
              - name: no-assert-ok
                type: {ttype}
                field: escalation
        """)
        result = parse_intent_test(path)
        assert result.tests[0].assertion == ""

    def test_severity_defaults_to_error(self, tmp_path):
        # VAL-SCHEMA-010
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: default-sev
                type: presence_check
                field: goals
        """)
        result = parse_intent_test(path)
        assert result.tests[0].severity == "error"

    def test_severity_preserves_warning(self, tmp_path):
        # VAL-SCHEMA-010
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: warn
                type: presence_check
                field: goals
                severity: warning
        """)
        result = parse_intent_test(path)
        assert result.tests[0].severity == "warning"

    def test_invalid_severity_raises(self, tmp_path):
        # VAL-SCHEMA-010
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: bad-sev
                type: presence_check
                field: goals
                severity: critical
        """)
        with pytest.raises(IntentTestSchemaError) as exc:
            parse_intent_test(path)
        assert any("severity" in m or "critical" in m for m in exc.value.errors)

    def test_unknown_per_case_field_rejected(self, tmp_path):
        # VAL-SCHEMA-011
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: typo
                type: presence_check
                field: goals
                fieldd: oops
        """)
        with pytest.raises(IntentTestSchemaError) as exc:
            parse_intent_test(path)
        assert any("fieldd" in m for m in exc.value.errors)


class TestAssertKeywordMapping:
    def test_assert_key_maps_to_assertion_attribute(self, tmp_path):
        # VAL-SCHEMA-012
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: mapping
                type: count_check
                assert: "len(goals) > 0"
        """)
        result = parse_intent_test(path)
        tc = result.tests[0]
        assert tc.assertion == "len(goals) > 0"
        assert not hasattr(tc, "assert")

    def test_to_dict_round_trips_assertion_back_to_assert(self, tmp_path):
        # VAL-SCHEMA-012
        path = _write(tmp_path, """
            name: suite
            tests:
              - name: mapping
                type: count_check
                assert: "len(goals) > 0"
        """)
        result = parse_intent_test(path)
        case_dict = result.tests[0].to_dict()
        assert case_dict["assert"] == "len(goals) > 0"
        assert "assertion" not in case_dict

    def test_intent_test_to_dict_includes_name_and_tests(self, tmp_path):
        path = _write(tmp_path, """
            name: suite
            description: d
            tests:
              - name: mapping
                type: presence_check
                field: goals
        """)
        result = parse_intent_test(path)
        as_dict = result.to_dict()
        assert as_dict["name"] == "suite"
        assert as_dict["description"] == "d"
        assert isinstance(as_dict["tests"], list)
        assert as_dict["tests"][0]["name"] == "mapping"


class TestPathArgument:
    def test_accepts_string_path(self, tmp_path):
        path = _write(tmp_path, """
            name: suite
            tests: []
        """)
        result = parse_intent_test(str(path))
        assert result.name == "suite"
