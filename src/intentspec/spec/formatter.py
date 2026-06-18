"""Error/output formatting for terminal display."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO


# ANSI color codes
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def _supports_color(stream: TextIO) -> bool:
    """Check if the output stream supports ANSI colors."""
    if not hasattr(stream, "isatty"):
        return False
    try:
        return stream.isatty()
    except Exception:
        return False


class Formatter:
    """Terminal output formatter with optional color support."""

    def __init__(self, use_color: bool | None = None, stream: TextIO | None = None):
        self.stream = stream or sys.stdout
        if use_color is None:
            self.color = _supports_color(self.stream)
        else:
            self.color = use_color

    def _c(self, text: str, *codes: str) -> str:
        """Wrap text in color codes if color is enabled."""
        if not self.color:
            return text
        return "".join(codes) + text + RESET

    def error(self, message: str) -> str:
        return self._c(f"  ✗ {message}", RED)

    def warning(self, message: str) -> str:
        return self._c(f"  ⚠ {message}", YELLOW)

    def success(self, message: str) -> str:
        return self._c(f"  ✓ {message}", GREEN)

    def info(self, message: str) -> str:
        return f"  {message}"

    def header(self, message: str) -> str:
        return self._c(message, BOLD)

    def subheader(self, message: str) -> str:
        return self._c(message, DIM)

    def format_validation_errors(
        self,
        path: Path,
        schema_errors: list[str],
        semantic_warnings: list[str],
    ) -> str:
        """Format validation results for display."""
        lines: list[str] = []

        if not schema_errors and not semantic_warnings:
            lines.append(self.success(f"{path}: valid"))
            return "\n".join(lines)

        total = len(schema_errors) + len(semantic_warnings)
        lines.append(self.header(f"{path}: {total} issue(s)"))

        for err in schema_errors:
            lines.append(self.error(err))

        for warn in semantic_warnings:
            lines.append(self.warning(warn))

        return "\n".join(lines)

    def format_score(self, agent_name: str, score: float, breakdown: dict[str, float]) -> str:
        """Format IDS score output."""
        lines: list[str] = []

        if score >= 80:
            color = GREEN
        elif score >= 50:
            color = YELLOW
        else:
            color = RED

        lines.append(self.header(f"Intent Debt Score for '{agent_name}':"))
        lines.append(f"  {self._c(f'~{score:.0f}/100', color, BOLD)}")
        lines.append("")
        lines.append(self.subheader("Breakdown:"))

        for component, value in breakdown.items():
            pct = value * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            lines.append(f"  {component:20s} {bar} {pct:.0f}%")

        return "\n".join(lines)

    def format_coverage(self, agent_name: str, coverage_pct: float, missing: list[str]) -> str:
        """Format coverage output."""
        lines: list[str] = []

        if coverage_pct >= 80:
            color = GREEN
        elif coverage_pct >= 50:
            color = YELLOW
        else:
            color = RED

        lines.append(self.header(f"Intent Coverage for '{agent_name}':"))
        lines.append(f"  {self._c(f'~{coverage_pct:.0f}%', color, BOLD)}")

        if missing:
            lines.append("")
            lines.append(self.subheader("Missing:"))
            for item in missing:
                lines.append(self.warning(item))

        return "\n".join(lines)
