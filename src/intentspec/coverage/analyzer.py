"""Coverage analysis — structural coverage of agent specs.

Measures what fraction of agent tools, goals, constraints, and non-negotiables
are documented in intent.yaml compared to what's mentioned in the source spec.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from intentspec.models.intent import Intent

_RE_TOOL_MENTION = re.compile(r"`([^`]+)`")
_RE_BULLET = re.compile(r"^\s*[-*]\s+(.+)")
_RE_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.+)")


def analyze_coverage(
    intent: Intent,
    source_path: Path | str | None = None,
    *,
    source_text: str | None = None,
) -> dict[str, Any]:
    """Analyze structural coverage of an intent against its source.

    Args:
        intent: The parsed Intent model.
        source_path: Path to the original AGENTS.md/SKILL.md file.
        source_text: Raw source text (alternative to source_path).

    Returns:
        Dict with coverage metrics:
        - tool_coverage: fraction of mentioned tools that are in intent.tools.allowed
        - goal_coverage: fraction of mentioned goals that are in intent.goals
        - constraint_coverage: fraction of mentioned constraints that are in intent.constraints
        - non_negotiable_coverage: fraction of mentioned non-negotiables that are in intent.non_negotiables
        - overall: weighted average of the above
        - missing_tools: list of tool names mentioned but not in intent
        - missing_goals: list of goal descriptions mentioned but not in intent
    """
    if source_text is None and source_path:
        try:
            source_text = Path(source_path).read_text(encoding="utf-8-sig")
        except OSError:
            source_text = ""

    if not source_text:
        return {
            "has_source": False,
            "tool_coverage": None,
            "goal_coverage": None,
            "constraint_coverage": None,
            "non_negotiable_coverage": None,
            "overall": None,
            "missing_tools": [],
            "missing_goals": [],
        }

    # Extract mentioned tools from source
    mentioned_tools = set()
    for match in _RE_TOOL_MENTION.finditer(source_text):
        tool = match.group(1).strip()
        if tool and len(tool) < 40:
            mentioned_tools.add(tool.lower())

    # Extract mentioned goals from source (bullets under Goals/Purpose/Overview sections)
    mentioned_goals = _extract_section_bullets(source_text, {"goals", "purpose", "what you do", "mission", "objectives", "overview"})

    # Extract mentioned constraints from source (bullets with MUST/NEVER/ALWAYS)
    mentioned_constraints = set()
    for line in source_text.split("\n"):
        m = _RE_BULLET.match(line) or _RE_NUMBERED.match(line)
        if m:
            text = m.group(1).strip()
            if re.match(r"^(MUST|NEVER|ALWAYS|DO NOT|REQUIRED TO|SHALL)\b", text, re.IGNORECASE):
                mentioned_constraints.add(re.sub(r"\s+", " ", text.lower()))

    # Extract mentioned non-negotiables from source (bullets with emphatic language)
    mentioned_non_negs = set()
    for line in source_text.split("\n"):
        m = _RE_BULLET.match(line) or _RE_NUMBERED.match(line)
        if m:
            text = m.group(1).strip()
            if re.match(r"^(NEVER|ABSOLUTELY|STRICTLY|UNDER NO CIRCUMSTANCES)\b", text, re.IGNORECASE):
                mentioned_non_negs.add(re.sub(r"\s+", " ", text.lower()))

    # Calculate coverage
    declared_tools = {t.name.lower() for t in intent.tools_allowed}
    tool_coverage = _calc_coverage(mentioned_tools, declared_tools)

    declared_goals = {re.sub(r"\s+", " ", g.description.lower()) for g in intent.goals}
    goal_coverage = _calc_coverage(set(mentioned_goals), declared_goals)

    declared_constraints = {re.sub(r"\s+", " ", c.rule.lower()) for c in intent.constraints}
    constraint_coverage = _calc_coverage(mentioned_constraints, declared_constraints)

    declared_non_negs = {re.sub(r"\s+", " ", nn.rule.lower()) for nn in intent.non_negotiables}
    non_neg_coverage = _calc_coverage(mentioned_non_negs, declared_non_negs)

    # Weighted average
    overall = (
        tool_coverage * 0.30 +
        goal_coverage * 0.25 +
        constraint_coverage * 0.25 +
        non_neg_coverage * 0.20
    )

    # Find missing items
    missing_tools = sorted(mentioned_tools - declared_tools)
    missing_goals = sorted(set(mentioned_goals) - declared_goals)

    return {
        "tool_coverage": tool_coverage,
        "goal_coverage": goal_coverage,
        "constraint_coverage": constraint_coverage,
        "non_negotiable_coverage": non_neg_coverage,
        "overall": overall,
        "missing_tools": missing_tools,
        "missing_goals": missing_goals,
    }


def _calc_coverage(mentioned: set[str], declared: set[str]) -> float:
    """Calculate coverage fraction."""
    if not mentioned:
        return 1.0  # Nothing mentioned = nothing to cover
    if not declared:
        return 0.0
    # Count how many mentioned items have a fuzzy match in declared
    matched = 0
    for m in mentioned:
        for d in declared:
            if m in d or d in m:
                matched += 1
                break
    return matched / len(mentioned)


def _extract_section_bullets(text: str, section_names: set[str]) -> list[str]:
    """Extract bullet items from sections with matching titles."""
    bullets = []
    current_section = None
    fence = False

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            fence = not fence
        if not fence:
            m = re.match(r"^#{1,3}\s+(.+)$", line)
            if m:
                title = m.group(1).strip().lower()
                current_section = title if title in section_names else None
                continue
        if current_section:
            m = _RE_BULLET.match(line) or _RE_NUMBERED.match(line)
            if m:
                bullets.append(m.group(1).strip())

    return bullets
