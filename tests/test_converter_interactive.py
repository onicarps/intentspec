"""Tests for converter/interactive.py — interactive review flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from intentspec.converter.interactive import (
    _confidence_color,
    _review_field,
    review_interactive,
)
from intentspec.converter.types import ParseResult
from intentspec.models.intent import (
    Constraint,
    Goal,
    Intent,
    NonNegotiable,
    ToolPermission,
)


def _make_result(**kwargs):
    """Helper to create a ParseResult for testing."""
    intent = Intent(
        agent_name=kwargs.get("agent_name", "test-agent"),
        agent_type=kwargs.get("agent_type", "custom"),
        agent_description=kwargs.get("agent_description", "A test agent"),
        goals=kwargs.get("goals", []),
        constraints=kwargs.get("constraints", []),
        non_negotiables=kwargs.get("non_negotiables", []),
        tools_allowed=kwargs.get("tools_allowed", []),
    )
    return ParseResult(
        intent=intent,
        confidences=kwargs.get("confidences", {}),
        sources=kwargs.get("sources", {}),
        warnings=kwargs.get("warnings", []),
        format=kwargs.get("format", "test"),
    )


class TestConfidenceColor:
    """Test _confidence_color helper."""

    def test_high_confidence_green(self):
        result = _confidence_color(0.8)
        assert "\x1b[32m" in result  # ANSI green

    def test_medium_confidence_yellow(self):
        result = _confidence_color(0.5)
        assert "\x1b[33m" in result  # ANSI yellow

    def test_low_confidence_red(self):
        result = _confidence_color(0.2)
        assert "\x1b[31m" in result  # ANSI red

    def test_boundary_high(self):
        """Exactly 0.75 should be green."""
        result = _confidence_color(0.75)
        assert "\x1b[32m" in result

    def test_boundary_medium(self):
        """Exactly 0.40 should be yellow."""
        result = _confidence_color(0.40)
        assert "\x1b[33m" in result

    def test_boundary_low(self):
        """Just below 0.40 should be red."""
        result = _confidence_color(0.39)
        assert "\x1b[31m" in result

    def test_zero_confidence(self):
        result = _confidence_color(0.0)
        assert "\x1b[31m" in result

    def test_one_confidence(self):
        result = _confidence_color(1.0)
        assert "\x1b[32m" in result


class TestReviewField:
    """Test _review_field helper."""

    def test_keep(self):
        with patch("intentspec.converter.interactive.click.prompt", return_value="k"):
            result = _review_field("name", "test-value", "agent.name")
        assert result == "test-value"

    def test_edit(self):
        with patch("intentspec.converter.interactive.click.prompt", side_effect=["e", "new-value"]):
            result = _review_field("name", "test-value", "agent.name")
        assert result == "new-value"

    def test_finish(self):
        with patch("intentspec.converter.interactive.click.prompt", return_value="f"):
            result = _review_field("name", "test-value", "agent.name")
        assert result == "test-value"


class TestReviewInteractive:
    """Test the main review_interactive function."""

    def test_keep_all_fields(self):
        """User keeps all fields as-is."""
        result = _make_result(
            agent_name="my-agent",
            agent_description="A test agent",
        )
        # Mock all prompts to return "k" (keep) or "f" (finish)
        with patch("intentspec.converter.interactive.click.prompt", return_value="k"):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.agent_name == "my-agent"
        assert reviewed.intent.agent_description == "A test agent"
        assert "User-reviewed via interactive mode" in reviewed.warnings

    def test_edit_agent_name(self):
        """User edits the agent name."""
        result = _make_result(agent_name="old-name", agent_description="A test agent")
        # First prompt is for agent name action, second is for new name
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["e", "new-name", "k", "k"],  # edit name, then keep rest
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.agent_name == "new-name"

    def test_edit_agent_description(self):
        """User edits the agent description."""
        result = _make_result(agent_name="test", agent_description="Old description")
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "e", "New description", "k", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.agent_description == "New description"

    def test_goals_keep(self):
        """User keeps all goals."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            goals=[
                Goal(description="Goal one", priority="high"),
                Goal(description="Goal two", priority="medium"),
            ],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "k", "k"],  # keep name, keep desc, keep goal1, keep goal2
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.goals) == 2

    def test_goals_edit(self):
        """User edits a goal."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            goals=[Goal(description="Old goal", priority="high")],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "e", "New goal", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.goals[0].description == "New goal"

    def test_goals_drop(self):
        """User drops a goal."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            goals=[
                Goal(description="Keep this", priority="high"),
                Goal(description="Drop this", priority="low"),
            ],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "k", "d", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.goals) == 1
        assert reviewed.intent.goals[0].description == "Keep this"

    def test_goals_finish(self):
        """User finishes review during goals."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            goals=[
                Goal(description="Goal one", priority="high"),
                Goal(description="Goal two", priority="medium"),
                Goal(description="Goal three", priority="low"),
            ],
        )
        # Keep first goal, finish (rest should be kept)
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "k", "f"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.goals) == 3

    def test_constraints_keep(self):
        """User keeps all constraints."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            constraints=[
                Constraint(rule="Always do X", enforceable=True),
                Constraint(rule="Never do Y", enforceable=False),
            ],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "k", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.constraints) == 2

    def test_constraints_edit(self):
        """User edits a constraint."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            constraints=[Constraint(rule="Old rule", enforceable=True)],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "e", "New rule", True, "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.constraints[0].rule == "New rule"

    def test_constraints_drop(self):
        """User drops a constraint."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            constraints=[
                Constraint(rule="Keep this", enforceable=True),
                Constraint(rule="Drop this", enforceable=False),
            ],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "k", "d", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.constraints) == 1

    def test_constraints_finish(self):
        """User finishes during constraint review."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            constraints=[
                Constraint(rule="Rule 1", enforceable=True),
                Constraint(rule="Rule 2", enforceable=False),
            ],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "f"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.constraints) == 2

    def test_non_negotiables_keep(self):
        """User keeps all non-negotiables."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            non_negotiables=[
                NonNegotiable(rule="Never do X", severity="hard"),
                NonNegotiable(rule="Always do Y", severity="soft"),
            ],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "k", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.non_negotiables) == 2

    def test_non_negotiables_edit(self):
        """User edits a non-negotiable."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            non_negotiables=[NonNegotiable(rule="Old rule", severity="hard")],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "e", "New rule", "soft", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.non_negotiables[0].rule == "New rule"
        assert reviewed.intent.non_negotiables[0].severity == "soft"

    def test_non_negotiables_drop(self):
        """User drops a non-negotiable."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            non_negotiables=[
                NonNegotiable(rule="Keep this", severity="hard"),
                NonNegotiable(rule="Drop this", severity="soft"),
            ],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "k", "d", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.non_negotiables) == 1

    def test_non_negotiables_finish(self):
        """User finishes during non-negotiable review."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            non_negotiables=[
                NonNegotiable(rule="NN 1", severity="hard"),
                NonNegotiable(rule="NN 2", severity="soft"),
            ],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "f"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.non_negotiables) == 2

    def test_empty_goals_skipped(self):
        """No goals means goal review is skipped."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            goals=[],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.goals == []

    def test_empty_constraints_skipped(self):
        """No constraints means constraint review is skipped."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            constraints=[],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.constraints == []

    def test_empty_non_negotiables_skipped(self):
        """No non-negotiables means non-negotiable review is skipped."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            non_negotiables=[],
        )
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.intent.non_negotiables == []

    def test_preserves_confidences_and_sources(self):
        """Reviewed result should preserve original confidences and sources."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            confidences={"agent.name": 0.9},
            sources={},
        )
        with patch("intentspec.converter.interactive.click.prompt", return_value="k"):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.confidences.get("agent.name") == 0.9

    def test_preserves_format(self):
        """Reviewed result should preserve the original format."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            format="agents_md",
        )
        with patch("intentspec.converter.interactive.click.prompt", return_value="k"):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert reviewed.format == "agents_md"

    def test_appends_user_reviewed_warning(self):
        """Reviewed result should have 'User-reviewed via interactive mode' warning."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            warnings=["Existing warning"],
        )
        with patch("intentspec.converter.interactive.click.prompt", return_value="k"):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert "Existing warning" in reviewed.warnings
        assert "User-reviewed via interactive mode" in reviewed.warnings

    def test_all_sections_with_finish(self):
        """Test with all sections populated, user finishes early."""
        result = _make_result(
            agent_name="test",
            agent_description="A test",
            goals=[
                Goal(description="Goal 1", priority="high"),
                Goal(description="Goal 2", priority="medium"),
            ],
            constraints=[
                Constraint(rule="Rule 1", enforceable=True),
                Constraint(rule="Rule 2", enforceable=False),
            ],
            non_negotiables=[
                NonNegotiable(rule="NN 1", severity="hard"),
                NonNegotiable(rule="NN 2", severity="soft"),
            ],
        )
        # Keep name, keep desc, keep goal1, finish goals, keep constraint1, finish constraints, keep nn1, finish nn
        with patch(
            "intentspec.converter.interactive.click.prompt",
            side_effect=["k", "k", "k", "f", "k", "f", "k", "f"],
        ):
            with patch("intentspec.converter.interactive.click.echo"):
                reviewed = review_interactive(result)
        assert len(reviewed.intent.goals) == 2
        assert len(reviewed.intent.constraints) == 2
        assert len(reviewed.intent.non_negotiables) == 2
