"""Tests for spec/formatter.py — Formatter class."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from intentspec.spec.formatter import (
    BOLD,
    DIM,
    GREEN,
    RED,
    RESET,
    YELLOW,
    Formatter,
    _supports_color,
)


class TestSupportsColor:
    """Test _supports_color helper."""

    def test_with_tty(self):
        stream = io.StringIO()
        # StringIO doesn't have isatty by default, but we can mock it
        stream.isatty = lambda: True  # type: ignore
        assert _supports_color(stream) is True

    def test_without_isatty(self):
        """Stream without isatty attribute should return False."""

        class NoIsatty:
            pass

        assert _supports_color(NoIsatty()) is False  # type: ignore[arg-type]

    def test_isatty_returns_false(self):
        stream = io.StringIO()
        stream.isatty = lambda: False  # type: ignore
        assert _supports_color(stream) is False

    def test_isatty_raises(self):
        stream = io.StringIO()
        stream.isatty = lambda: (_ for _ in ()).throw(Exception("boom"))  # type: ignore
        assert _supports_color(stream) is False


class TestFormatterInit:
    """Test Formatter initialization."""

    def test_default_stream_is_stdout(self):
        fmt = Formatter(use_color=False)
        assert fmt.stream is sys.stdout

    def test_custom_stream(self):
        stream = io.StringIO()
        fmt = Formatter(use_color=False, stream=stream)
        assert fmt.stream is stream

    def test_color_auto_detect_tty(self):
        stream = io.StringIO()
        stream.isatty = lambda: True  # type: ignore
        fmt = Formatter(stream=stream)
        assert fmt.color is True

    def test_color_auto_detect_no_tty(self):
        stream = io.StringIO()
        fmt = Formatter(stream=stream)
        assert fmt.color is False

    def test_color_forced_on(self):
        fmt = Formatter(use_color=True)
        assert fmt.color is True

    def test_color_forced_off(self):
        fmt = Formatter(use_color=False)
        assert fmt.color is False


class TestFormatterColor:
    """Test the _c color helper."""

    def test_color_disabled(self):
        fmt = Formatter(use_color=False)
        result = fmt._c("hello", RED)
        assert result == "hello"

    def test_color_enabled(self):
        fmt = Formatter(use_color=True)
        result = fmt._c("hello", RED)
        assert RED in result
        assert "hello" in result
        assert RESET in result

    def test_multiple_codes(self):
        fmt = Formatter(use_color=True)
        result = fmt._c("hello", BOLD, RED)
        assert BOLD in result
        assert RED in result
        assert RESET in result


class TestFormatterError:
    """Test error formatting."""

    def test_error_no_color(self):
        fmt = Formatter(use_color=False)
        result = fmt.error("test error")
        assert "✗ test error" in result

    def test_error_with_color(self):
        fmt = Formatter(use_color=True)
        result = fmt.error("test error")
        assert "test error" in result
        assert RED in result


class TestFormatterWarning:
    """Test warning formatting."""

    def test_warning_no_color(self):
        fmt = Formatter(use_color=False)
        result = fmt.warning("test warning")
        assert "⚠ test warning" in result

    def test_warning_with_color(self):
        fmt = Formatter(use_color=True)
        result = fmt.warning("test warning")
        assert "test warning" in result
        assert YELLOW in result


class TestFormatterSuccess:
    """Test success formatting."""

    def test_success_no_color(self):
        fmt = Formatter(use_color=False)
        result = fmt.success("test success")
        assert "✓ test success" in result

    def test_success_with_color(self):
        fmt = Formatter(use_color=True)
        result = fmt.success("test success")
        assert "test success" in result
        assert GREEN in result


class TestFormatterInfo:
    """Test info formatting."""

    def test_info(self):
        fmt = Formatter(use_color=False)
        result = fmt.info("test info")
        assert "test info" in result

    def test_info_no_color_codes(self):
        fmt = Formatter(use_color=True)
        result = fmt.info("test info")
        # info() doesn't use color
        assert result == "  test info"


class TestFormatterHeader:
    """Test header formatting."""

    def test_header_no_color(self):
        fmt = Formatter(use_color=False)
        result = fmt.header("test header")
        assert "test header" in result

    def test_header_with_color(self):
        fmt = Formatter(use_color=True)
        result = fmt.header("test header")
        assert "test header" in result
        assert BOLD in result


class TestFormatterSubheader:
    """Test subheader formatting."""

    def test_subheader_no_color(self):
        fmt = Formatter(use_color=False)
        result = fmt.subheader("test subheader")
        assert "test subheader" in result

    def test_subheader_with_color(self):
        fmt = Formatter(use_color=True)
        result = fmt.subheader("test subheader")
        assert "test subheader" in result
        assert DIM in result


class TestFormatValidationErrors:
    """Test format_validation_errors method."""

    def test_valid_no_issues(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_validation_errors(Path("test.yaml"), [], [])
        assert "valid" in result

    def test_with_schema_errors(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_validation_errors(
            Path("test.yaml"),
            ["error 1", "error 2"],
            [],
        )
        assert "error 1" in result
        assert "error 2" in result
        assert "2 issue(s)" in result

    def test_with_semantic_warnings(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_validation_errors(
            Path("test.yaml"),
            [],
            ["warning 1"],
        )
        assert "warning 1" in result
        assert "1 issue(s)" in result

    def test_with_both_errors_and_warnings(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_validation_errors(
            Path("test.yaml"),
            ["error 1"],
            ["warning 1", "warning 2"],
        )
        assert "error 1" in result
        assert "warning 1" in result
        assert "3 issue(s)" in result

    def test_path_in_output(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_validation_errors(
            Path("/some/path.yaml"),
            ["error 1"],
            [],
        )
        assert "/some/path.yaml" in result


class TestFormatScore:
    """Test format_score method."""

    def test_high_score_green(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_score("my-agent", 85.0, {"tool_coverage": 0.9})
        assert "85/100" in result or "~85/100" in result
        assert "my-agent" in result
        assert GREEN in result

    def test_medium_score_yellow(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_score("my-agent", 60.0, {"tool_coverage": 0.5})
        assert YELLOW in result

    def test_low_score_red(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_score("my-agent", 30.0, {"tool_coverage": 0.2})
        assert RED in result

    def test_score_breakdown(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_score(
            "my-agent",
            75.0,
            {
                "tool_coverage": 0.8,
                "goal_coverage": 0.6,
            },
        )
        assert "tool_coverage" in result
        assert "goal_coverage" in result
        assert "Breakdown:" in result

    def test_score_bar_chart(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_score(
            "my-agent",
            50.0,
            {"tool_coverage": 0.5},
        )
        # Should contain bar characters
        assert "█" in result
        assert "░" in result

    def test_score_boundary_80(self):
        """Score of exactly 80 should be green."""
        fmt = Formatter(use_color=True)
        result = fmt.format_score("agent", 80.0, {"tool_coverage": 1.0})
        assert GREEN in result

    def test_score_boundary_50(self):
        """Score of exactly 50 should be yellow."""
        fmt = Formatter(use_color=True)
        result = fmt.format_score("agent", 50.0, {"tool_coverage": 0.5})
        assert YELLOW in result

    def test_score_just_below_50(self):
        """Score of 49 should be red."""
        fmt = Formatter(use_color=True)
        result = fmt.format_score("agent", 49.0, {"tool_coverage": 0.49})
        assert RED in result


class TestFormatCoverage:
    """Test format_coverage method."""

    def test_high_coverage_green(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_coverage("my-agent", 85.0, [])
        assert "85%" in result or "~85%" in result
        assert "my-agent" in result
        assert GREEN in result

    def test_medium_coverage_yellow(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_coverage("my-agent", 60.0, [])
        assert YELLOW in result

    def test_low_coverage_red(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_coverage("my-agent", 30.0, [])
        assert RED in result

    def test_coverage_with_missing(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_coverage(
            "my-agent",
            50.0,
            ["missing_tool1", "missing_goal1"],
        )
        assert "Missing:" in result
        assert "missing_tool1" in result
        assert "missing_goal1" in result

    def test_coverage_without_missing(self):
        fmt = Formatter(use_color=False)
        result = fmt.format_coverage("my-agent", 100.0, [])
        assert "Missing:" not in result

    def test_coverage_boundary_80(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_coverage("agent", 80.0, [])
        assert GREEN in result

    def test_coverage_boundary_50(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_coverage("agent", 50.0, [])
        assert YELLOW in result

    def test_coverage_just_below_50(self):
        fmt = Formatter(use_color=True)
        result = fmt.format_coverage("agent", 49.0, [])
        assert RED in result
