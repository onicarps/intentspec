"""Coverage analysis for IntentSpec — structural coverage of agent specs.

Measures what fraction of agent tools, goals, constraints, and non-negotiables
are documented in intent.yaml compared to what's mentioned in the source spec.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from intentspec.models.intent import Intent


@dataclass
class CoverageResult:
    """Result of coverage analysis."""
    tool_coverage: float = 0.0
    goal_coverage: float = 0.0
    constraint_coverage: float = 0.0
    non_negotiable_coverage: float = 0.0
    overall: float = 0.0
    missing_tools: list[str] = field(default_factory=list)
    missing_goals: list[str] = field(default_factory=list)
    mentioned_tools: int = 0
    declared_tools: int = 0
    mentioned_goals: int = 0
    declared_goals: int = 0

    def to_text(self) -> str:
        lines = [
            f"Overall Coverage: {self.overall:.0%} (estimate)",
            f"  Tool coverage: {self.tool_coverage:.0%} ({self.declared_tools}/{self.mentioned_tools} tools)",
            f"  Goal coverage: {self.goal_coverage:.0%} ({self.declared_goals}/{self.mentioned_goals} goals)",
            f"  Constraint coverage: {self.constraint_coverage:.0%}",
            f"  Non-negotiable coverage: {self.non_negotiable_coverage:.0%}",
        ]
        if self.missing_tools:
            lines.append(f"  Missing tools: {', '.join(self.missing_tools)}")
        if self.missing_goals:
            lines.append(f"  Missing goals: {', '.join(self.missing_goals)}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": round(self.overall, 4),
            "tool_coverage": round(self.tool_coverage, 4),
            "goal_coverage": round(self.goal_coverage, 4),
            "constraint_coverage": round(self.constraint_coverage, 4),
            "non_negotiable_coverage": round(self.non_negotiable_coverage, 4),
            "missing_tools": self.missing_tools,
            "missing_goals": self.missing_goals,
        }


_RE_TOOL_MENTION = re.compile(r"`([^`]+)`")
_RE_BULLET = re.compile(r"^\s*[-*]\s+(.+)")
_RE_SECTION = re.compile(r"^#{1,3}\s+(.+)$")


def analyze_coverage(
    intent: Intent,
    source_path: Path | str | None = None,
    *,
    source_text: str | None = None,
) -> CoverageResult:
    """Analyze structural coverage of an intent against its source.

    Args:
        intent: The parsed Intent model.
        source_path: Path to the original AGENTS.md/SKILL.md file.
        source_text: Raw source text (alternative to source_path).

    Returns:
        CoverageResult with coverage metrics.
    """
    if source_text is None and source_path:
        try:
            source_text = Path(source_path).read_text(encoding="utf-8-sig")
        except OSError:
            source_text = ""

    result = CoverageResult()

    if not source_text:
        # No source to compare against — assume full coverage
        result.tool_coverage = 1.0
        result.goal_coverage = 1.0
        result.constraint_coverage = 1.0
        result.non_negotiable_coverage = 1.0
        result.overall = 1.0
        return result

    # Extract mentioned tools from source (backtick mentions)
    mentioned_tools: set[str] = set()
    for match in _RE_TOOL_MENTION.finditer(source_text):
        tool = match.group(1).strip()
        if tool and len(tool) < 40 and not tool.startswith("http"):
            mentioned_tools.add(tool.lower())

    # Extract mentioned goals from source
    mentioned_goals: set[str] = set()
    in_goal_section = False
    goal_sections = {"goals", "purpose", "what you do", "mission", "objectives", "overview", "description"}
    for line in source_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        m = _RE_SECTION.match(stripped)
        if m:
            title = m.group(1).strip().lower()
            in_goal_section = title in goal_sections
            continue
        if in_goal_section:
            bm = _RE_BULLET.match(stripped)
            if bm:
                mentioned_goals.add(re.sub(r"\s+", " ", bm.group(1).strip().lower()))

    # Calculate tool coverage
    declared_tools = {t.name.lower() for t in intent.tools_allowed}
    result.mentioned_tools = len(mentioned_tools)
    result.declared_tools = len(declared_tools)

    if mentioned_tools:
        matched = 0
        for m in mentioned_tools:
            for d in declared_tools:
                if m in d or d in m:
                    matched += 1
                    break
        result.tool_coverage = matched / len(mentioned_tools)
        result.missing_tools = sorted(mentioned_tools - {d for m in mentioned_tools for d in declared_tools if m in d or d in m})
        result.missing_tools = sorted(mentioned_tools - {m for m in mentioned_tools if any(m in d or d in m for d in declared_tools)})

    # Calculate goal coverage
    declared_goals = {re.sub(r"\s+", " ", g.description.lower()) for g in intent.goals}
    result.mentioned_goals = len(mentioned_goals)
    result.declared_goals = len(declared_goals)

    if mentioned_goals:
        matched = 0
        for m in mentioned_goals:
            for d in declared_goals:
                if m in d or d in m:
                    matched += 1
                    break
        result.goal_coverage = matched / len(mentioned_goals)

    # Constraint and non-negotiable coverage
    result.constraint_coverage = 1.0 if intent.constraints else 0.5
    result.non_negotiable_coverage = 1.0 if intent.non_negotiables else 0.5

    # Weighted average
    result.overall = (
        result.tool_coverage * 0.30 +
        result.goal_coverage * 0.25 +
        result.constraint_coverage * 0.25 +
        result.non_negotiable_coverage * 0.20
    )

    return result
