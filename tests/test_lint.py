"""Tests for lint rules engine v2."""

from __future__ import annotations

import pytest

from intentspec import lint as lint_module
from intentspec.lint import (
    LintResult,
    lint_intent,
    parse_disabled_rules,
)
from intentspec.models.intent import (
    Boundary,
    Constraint,
    Escalation,
    FailureMode,
    Goal,
    Intent,
    NonNegotiable,
    ToolPermission,
)


def _intent(**kwargs) -> Intent:
    defaults = {
        "agent_name": "test-agent",
        "agent_type": "coding",
        "agent_description": "A well-described test agent for lint checks",
        "goals": [
            Goal(
                description="Deliver reliable automated test coverage",
                priority="high",
                success_criteria="All unit tests pass in CI",
            )
        ],
        "constraints": [Constraint(rule="Must not delete production data", enforceable=True)],
        "non_negotiables": [NonNegotiable(rule="Never expose secrets", severity="hard")],
        "tools_allowed": [ToolPermission(name="read_file", rationale="Inspect repository files")],
        "tools_denied": [ToolPermission(name="rm_rf", rationale="Prevent destructive deletes")],
        "boundaries": [Boundary(scope="Unit tests", out_of_scope="Production deploys")],
        "escalation": Escalation(trigger="Repeated failures", method="Human review"),
        "failure_modes": [FailureMode(mode="Timeout", mitigation="Retry with backoff")],
    }
    defaults.update(kwargs)
    return Intent(**defaults)


class TestLintResult:
    def test_is_clean_when_no_issues(self):
        result = lint_intent(_intent())
        assert result.is_clean

    def test_is_clean_false_on_errors(self):
        result = lint_intent(_intent(goals=[]))
        assert not result.is_clean
        assert result.error_count > 0


class TestParseDisabledRules:
    def test_parses_disable_comment(self):
        content = "# intentspec: disable=goals-required\nversion: '1.0'\n"
        assert parse_disabled_rules(content) == {"goals-required"}

    def test_parses_multiple_disables(self):
        content = (
            "# intentspec: disable=goals-required\n"
            "# intentspec: disable=missing-escalation\n"
        )
        assert parse_disabled_rules(content) == {"goals-required", "missing-escalation"}


class TestAgentDescriptionRules:
    def test_short_description_warns(self):
        result = lint_intent(_intent(agent_description="short"))
        assert any(i.rule == "agent-description" for i in result.issues)

    def test_long_description_warns(self):
        result = lint_intent(_intent(agent_description="x" * 201))
        assert any(i.rule == "agent-description-length" for i in result.issues)

    def test_placeholder_description_warns(self):
        result = lint_intent(_intent(agent_description="TODO"))
        assert any(i.rule == "empty-description" for i in result.issues)


class TestGoalRules:
    def test_missing_goals_errors(self):
        result = lint_intent(_intent(goals=[]))
        assert any(i.rule == "goals-required" and i.severity == "error" for i in result.issues)

    def test_short_goal_description_warns(self):
        result = lint_intent(_intent(goals=[Goal(description="tiny")]))
        assert any(i.rule == "goal-description-length" for i in result.issues)

    def test_placeholder_goal_warns(self):
        result = lint_intent(_intent(goals=[Goal(description="TBD")]))
        assert any(i.rule == "empty-description" for i in result.issues)

    def test_missing_success_criteria_warns(self):
        result = lint_intent(_intent(goals=[Goal(description="Ship the quarterly release notes")]))
        assert any(i.rule == "goal-without-success-criteria" for i in result.issues)

    def test_duplicate_goals_warns(self):
        goals = [
            Goal(description="Improve test coverage across modules"),
            Goal(description="Improve test coverage across modules!"),
        ]
        result = lint_intent(_intent(goals=goals))
        assert any(i.rule == "duplicate-goals" for i in result.issues)


class TestConstraintRules:
    def test_unenforceable_constraint_text_warns(self):
        result = lint_intent(
            _intent(constraints=[Constraint(rule="Be thoughtful", enforceable=True)])
        )
        assert any(i.rule == "unenforceable-constraint" for i in result.issues)

    def test_enforceable_constraint_with_keywords_passes(self):
        result = lint_intent(
            _intent(constraints=[Constraint(rule="Must never delete files", enforceable=True)])
        )
        assert all(i.rule != "unenforceable-constraint" for i in result.issues)


class TestToolRules:
    def test_missing_rationale_warns(self):
        result = lint_intent(
            _intent(tools_allowed=[ToolPermission(name="git", rationale="")])
        )
        assert any(i.rule == "tool-rationale" for i in result.issues)

    def test_duplicate_tool_errors(self):
        tools = [
            ToolPermission(name="git", rationale="Version control"),
            ToolPermission(name="Git", rationale="Duplicate name"),
        ]
        result = lint_intent(_intent(tools_allowed=tools))
        assert any(i.rule == "duplicate-tool" and i.severity == "error" for i in result.issues)

    def test_tool_not_in_source_warns(self):
        result = lint_intent(
            _intent(tools_allowed=[ToolPermission(name="phantom_tool", rationale="Needed for tests")]),
            source_text="This document only mentions read_file.",
        )
        assert any(i.rule == "tools-not-in-source" for i in result.issues)

    def test_tool_in_source_passes(self):
        result = lint_intent(
            _intent(tools_allowed=[ToolPermission(name="read_file", rationale="Inspect files")]),
            source_text="Use read_file to inspect repository files.",
        )
        assert all(i.rule != "tools-not-in-source" for i in result.issues)

    def test_missing_denied_tools_warns(self):
        result = lint_intent(_intent(tools_denied=[]))
        assert any(i.rule == "missing-denied-tools" for i in result.issues)


class TestNonNegotiableRules:
    def test_invalid_severity_errors(self):
        result = lint_intent(
            _intent(non_negotiables=[NonNegotiable(rule="No leaks", severity="critical")])
        )
        assert any(i.rule == "non-negotiable-severity" for i in result.issues)


class TestOptionalSectionRules:
    def test_missing_escalation_warns(self):
        result = lint_intent(_intent(escalation=None))
        assert any(i.rule == "missing-escalation" for i in result.issues)

    def test_missing_failure_modes_warns(self):
        result = lint_intent(_intent(failure_modes=[]))
        assert any(i.rule == "missing-failure-modes" for i in result.issues)

    def test_missing_boundaries_warns(self):
        result = lint_intent(_intent(boundaries=[]))
        assert any(i.rule == "missing-boundaries" for i in result.issues)


class TestDisableRules:
    def test_disable_comment_suppresses_rule(self):
        content = "# intentspec: disable=goals-required\n"
        result = lint_intent(_intent(goals=[]), raw_content=content)
        assert all(i.rule != "goals-required" for i in result.issues)

    def test_disabled_rules_argument(self):
        result = lint_intent(_intent(goals=[]), disabled_rules={"goals-required"})
        assert all(i.rule != "goals-required" for i in result.issues)


class TestLintRegistrySize:
    def test_has_at_least_fifteen_rules(self):
        registered = {name for name, _ in lint_module._RULES}
        registered |= {name for name, _ in lint_module._LIST_RULES}
        assert len(registered) >= 15