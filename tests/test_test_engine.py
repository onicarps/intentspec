"""Tests for the structural assertion engine (``test_engine.py``).

Covers all five assertion types (presence/count/constraint/regex/cross_reference)
plus aggregation, severity handling, error isolation, security, serialization, and
performance, per VAL-ENGINE-001..019 and VAL-NFR-002 in the validation contract.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pytest

from intentspec.models.intent import Intent
from intentspec.test_engine import (
    TestResult,
    run_intent_tests,
)
from intentspec.test_schema import IntentTest, TestCase


def make_intent(**intent_block) -> Intent:
    """Build an Intent from an intent.yaml-shaped dict.

    Keyword args populate the top-level ``intent:`` block; ``agent`` /
    ``metadata`` may also be supplied to override the defaults.
    """
    agent = intent_block.pop("agent", {"name": "my-agent", "type": "coding", "description": "x"})
    metadata = intent_block.pop("metadata", None)
    data = {"version": "1.0", "agent": agent, "intent": intent_block}
    if metadata is not None:
        data["metadata"] = metadata
    return Intent.from_dict(data)


def suite_of(*cases: TestCase, name: str = "suite") -> IntentTest:
    return IntentTest(name=name, tests=list(cases))


def run_one(intent: Intent, case: TestCase) -> TestResult:
    result = run_intent_tests(intent, suite_of(case))
    assert len(result.tests) == 1
    return result.tests[0]


class TestPresenceCheck:
    def test_presence_passes_on_populated_field(self):
        intent = make_intent(escalation={"trigger": "on error", "method": "human"})
        case = TestCase(name="esc-present", type="presence_check",
                        field="escalation", assertion="escalation is not null")
        suite = run_intent_tests(intent, suite_of(case))
        assert suite.tests[0].passed is True
        assert suite.passed == 1

    def test_presence_fails_on_absent_field_naming_it(self):
        intent = make_intent(goals=[{"description": "g"}])  # no escalation
        case = TestCase(name="esc-absent", type="presence_check",
                        field="escalation", assertion="escalation is not null")
        suite = run_intent_tests(intent, suite_of(case))
        tr = suite.tests[0]
        assert tr.passed is False
        assert "escalation" in tr.message
        assert suite.failed == 1

    def test_presence_fails_on_empty_collection(self):
        intent = make_intent(goals=[])  # empty goals
        case = TestCase(name="goals-empty", type="presence_check",
                        field="goals", assertion="goals is not empty")
        tr = run_one(intent, case)
        assert tr.passed is False
        assert "goals" in tr.message


class TestCountCheck:
    def test_count_passes_simple_operator(self):
        intent = make_intent(goals=[{"description": "a"}, {"description": "b"}])
        case = TestCase(name="goals-count", type="count_check", assertion="len(goals) > 0")
        assert run_one(intent, case).passed is True

    def test_count_passes_filtered_form(self):
        intent = make_intent(non_negotiables=[
            {"rule": "no secrets", "severity": "hard"},
            {"rule": "be nice", "severity": "soft"},
        ])
        case = TestCase(name="hard-nn", type="count_check",
                        assertion="len(non_negotiables[severity='hard']) >= 1")
        assert run_one(intent, case).passed is True

    def test_count_fails_when_operator_violated(self):
        intent = make_intent(goals=[])
        case = TestCase(name="no-goals", type="count_check", assertion="len(goals) > 0")
        tr = run_one(intent, case)
        assert tr.passed is False
        assert "goals" in tr.message

    def test_count_fails_upper_bound(self):
        allowed = [{"name": f"t{i}", "rationale": "r"} for i in range(11)]
        intent = make_intent(tools={"allowed": allowed})
        case = TestCase(name="too-many", type="count_check", assertion="len(tools.allowed) <= 10")
        tr = run_one(intent, case)
        assert tr.passed is False


class TestConstraintCheck:
    def _disjoint_intent(self) -> Intent:
        return make_intent(tools={
            "allowed": [{"name": "read", "rationale": "r"}],
            "denied": [{"name": "delete", "rationale": "r"}],
        })

    def _overlap_intent(self) -> Intent:
        return make_intent(tools={
            "allowed": [{"name": "read", "rationale": "r"}, {"name": "shell", "rationale": "r"}],
            "denied": [{"name": "shell", "rationale": "r"}],
        })

    def test_constraint_passes_when_disjoint_unicode(self):
        case = TestCase(name="disjoint", type="constraint_check",
                        assertion="tools.denied ∩ tools.allowed == ∅")
        assert run_one(self._disjoint_intent(), case).passed is True

    def test_constraint_passes_when_disjoint_ascii(self):
        case = TestCase(name="disjoint-ascii", type="constraint_check",
                        assertion="tools.denied intersect tools.allowed == empty")
        assert run_one(self._disjoint_intent(), case).passed is True

    def test_constraint_fails_naming_overlap(self):
        case = TestCase(name="overlap", type="constraint_check",
                        assertion="tools.denied ∩ tools.allowed == ∅")
        tr = run_one(self._overlap_intent(), case)
        assert tr.passed is False
        assert "shell" in tr.message

    def test_unicode_and_ascii_give_identical_outcomes(self):
        intent = self._overlap_intent()
        unicode_case = TestCase(name="u", type="constraint_check",
                                assertion="tools.denied ∩ tools.allowed == ∅")
        ascii_case = TestCase(name="a", type="constraint_check",
                              assertion="tools.denied intersect tools.allowed == empty")
        assert run_one(intent, unicode_case).passed == run_one(intent, ascii_case).passed


class TestRegexCheck:
    def test_regex_passes_on_match(self):
        intent = make_intent(agent={"name": "my-agent", "type": "coding", "description": "x"})
        case = TestCase(name="name-ok", type="regex_check",
                        field="agent.name", assertion="^[a-z][a-z0-9-]*$")
        assert run_one(intent, case).passed is True

    def test_regex_fails_on_non_match(self):
        intent = make_intent(agent={"name": "My_Agent", "type": "coding", "description": "x"})
        case = TestCase(name="name-bad", type="regex_check",
                        field="agent.name", assertion="^[a-z][a-z0-9-]*$")
        tr = run_one(intent, case)
        assert tr.passed is False
        assert "My_Agent" in tr.message

    def test_malformed_regex_is_error_not_crash(self):
        intent = make_intent(agent={"name": "x", "type": "coding", "description": "x"})
        case = TestCase(name="bad-regex", type="regex_check",
                        field="agent.name", assertion="^[a-z")
        suite = run_intent_tests(intent, suite_of(case))
        tr = suite.tests[0]
        assert tr.passed is False
        assert tr.error is True
        assert suite.errors == 1


class TestCrossReference:
    def test_cross_reference_passes_conditional(self):
        intent = make_intent(sub_agents=["child"], extends="parent.yaml")
        case = TestCase(name="extends-set", type="cross_reference",
                        assertion="extends non-empty when sub_agents set")
        assert run_one(intent, case).passed is True

    def test_cross_reference_passes_subset(self):
        intent = make_intent(sub_agents=["read"],
                             tools={"allowed": [{"name": "read", "rationale": "r"}]})
        case = TestCase(name="subset", type="cross_reference",
                        assertion="every x in sub_agents subset tools.allowed")
        assert run_one(intent, case).passed is True

    def test_cross_reference_fails_naming_unresolved(self):
        intent = make_intent(sub_agents=["child"], extends="")
        case = TestCase(name="extends-missing", type="cross_reference",
                        assertion="extends non-empty when sub_agents set")
        tr = run_one(intent, case)
        assert tr.passed is False
        assert "extends" in tr.message

    def test_cross_reference_subset_fails_naming_member(self):
        intent = make_intent(sub_agents=["ghost"],
                             tools={"allowed": [{"name": "read", "rationale": "r"}]})
        case = TestCase(name="subset-bad", type="cross_reference",
                        assertion="every x in sub_agents subset tools.allowed")
        tr = run_one(intent, case)
        assert tr.passed is False
        assert "ghost" in tr.message


class TestAggregationAndSeverity:
    def test_mixed_suite_counts(self):
        intent = make_intent(goals=[{"description": "g"}])
        passing = TestCase(name="p", type="count_check", assertion="len(goals) > 0")
        failing = TestCase(name="f", type="count_check", assertion="len(goals) > 5")
        unparseable = TestCase(name="e", type="constraint_check", assertion="this is gibberish")
        suite = run_intent_tests(intent, suite_of(passing, failing, unparseable))
        assert suite.passed == 1
        assert suite.failed == 1
        assert suite.errors == 1
        assert len(suite.tests) == 3

    def test_total_duration_is_sum_of_per_test(self):
        intent = make_intent(goals=[{"description": "g"}])
        cases = [
            TestCase(name="a", type="count_check", assertion="len(goals) > 0"),
            TestCase(name="b", type="presence_check", field="goals", assertion="goals is not empty"),
        ]
        suite = run_intent_tests(intent, suite_of(*cases))
        for tr in suite.tests:
            assert tr.duration_ms >= 0.0
        assert suite.total_duration_ms == pytest.approx(sum(t.duration_ms for t in suite.tests))

    def test_warning_severity_failure_distinguished(self):
        intent = make_intent(goals=[])
        case = TestCase(name="warn", type="count_check", assertion="len(goals) > 0",
                        severity="warning")
        suite = run_intent_tests(intent, suite_of(case))
        tr = suite.tests[0]
        assert tr.passed is False
        assert tr.severity == "warning"
        assert suite.failed == 0
        assert suite.warnings == 1

    def test_unparseable_is_isolated_subsequent_still_run(self):
        intent = make_intent(goals=[{"description": "g"}])
        unparseable = TestCase(name="bad", type="count_check", assertion="len(goals) ?? 0")
        good = TestCase(name="good", type="count_check", assertion="len(goals) > 0")
        suite = run_intent_tests(intent, suite_of(unparseable, good))
        assert suite.tests[0].passed is False
        assert suite.tests[0].error is True
        assert suite.tests[1].passed is True
        assert suite.errors == 1
        assert suite.passed == 1


class TestSecurity:
    def test_assertion_with_python_code_has_no_side_effect(self, tmp_path: Path):
        marker = tmp_path / "pwned"
        intent = make_intent(goals=[{"description": "g"}])
        payload = f"__import__('os').system('touch {marker}')"
        case = TestCase(name="evil", type="constraint_check", assertion=payload)
        suite = run_intent_tests(intent, suite_of(case))
        assert not marker.exists()
        assert suite.tests[0].error is True

    def test_engine_source_has_no_eval_exec_compile(self):
        import intentspec.test_engine as engine

        source = Path(engine.__file__).read_text(encoding="utf-8")
        assert "eval(" not in source
        assert "exec(" not in source
        for match in re.finditer(r"(?<![.\w])compile\(", source):
            preceding = source[max(0, match.start() - 3):match.start()]
            assert preceding.endswith("re."), "compile() must only be re.compile()"


class TestSerialization:
    def test_to_dict_is_json_serializable_with_counts(self):
        intent = make_intent(goals=[{"description": "g"}])
        case = TestCase(name="p", type="count_check", assertion="len(goals) > 0")
        suite = run_intent_tests(intent, suite_of(case))
        d = suite.to_dict()
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert decoded["passed"] == 1
        assert "failed" in decoded and "errors" in decoded
        assert "total_duration_ms" in decoded
        assert isinstance(decoded["tests"], list)
        entry = decoded["tests"][0]
        assert entry["name"] == "p"
        assert entry["passed"] is True
        assert "severity" in entry and "message" in entry

    def test_to_text_is_non_empty_and_consistent(self):
        intent = make_intent(goals=[{"description": "g"}])
        case = TestCase(name="p", type="count_check", assertion="len(goals) > 0")
        suite = run_intent_tests(intent, suite_of(case))
        text = suite.to_text()
        assert isinstance(text, str)
        assert text.strip()
        assert "p" in text


class TestPerformance:
    def test_all_five_types_under_100ms(self):
        intent = make_intent(
            agent={"name": "my-agent", "type": "coding", "description": "x"},
            goals=[{"description": "a"}, {"description": "b"}],
            non_negotiables=[{"rule": "no secrets", "severity": "hard"}],
            sub_agents=["read"],
            extends="parent.yaml",
            tools={
                "allowed": [{"name": "read", "rationale": "r"}],
                "denied": [{"name": "delete", "rationale": "r"}],
            },
        )
        cases = [
            TestCase(name="presence", type="presence_check", field="goals",
                     assertion="goals is not empty"),
            TestCase(name="count", type="count_check",
                     assertion="len(non_negotiables[severity='hard']) >= 1"),
            TestCase(name="constraint", type="constraint_check",
                     assertion="tools.denied ∩ tools.allowed == ∅"),
            TestCase(name="regex", type="regex_check", field="agent.name",
                     assertion="^[a-z][a-z0-9-]*$"),
            TestCase(name="cross", type="cross_reference",
                     assertion="extends non-empty when sub_agents set"),
        ]
        start = time.perf_counter()
        suite = run_intent_tests(intent, suite_of(*cases))
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 100.0
        assert suite.total_duration_ms < 100.0
        assert suite.passed == 5
