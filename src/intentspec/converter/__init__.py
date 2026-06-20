"""Public converter API: parse() and parse_quickstart()."""

from __future__ import annotations

import re
from pathlib import Path

from intentspec.adapters.crewai import parse_crewai
from intentspec.adapters.langgraph import parse_langgraph
from intentspec.converter.agents_md import parse_agents_md
from intentspec.converter.agentskills import parse_agentskills
from intentspec.converter.format_detect import detect_format
from intentspec.converter.skill_md import parse_skill_md
from intentspec.converter.types import ConverterError, FieldSource, ParseResult
from intentspec.models.intent import Intent, NonNegotiable, ToolPermission


__all__ = [
    "parse",
    "parse_quickstart",
    "parse_agents_md",
    "parse_skill_md",
    "parse_agentskills",
    "parse_langgraph",
    "ParseResult",
    "FieldSource",
    "ConverterError",
]


_VALID_AGENT_TYPES = {"coding", "research", "service", "data", "coordinator", "custom"}


def parse(
    path: Path | str,
    *,
    use_llm: bool = False,
    format: str | None = None,
) -> ParseResult:
    """Parse an agent specification source into a ParseResult.

    Args:
        path: Path to a markdown file (AGENTS.md / SKILL.md) or an agentskills
            directory.
        use_llm: When True, attempt LLM augmentation (placeholder until F8).
        format: When set, forces the format detector. One of "agents_md",
            "skill_md", "agentskills". When None, auto-detection is used.

    Returns:
        A ParseResult with a minimal-but-valid Intent and provenance metadata.

    Raises:
        ConverterError: If the path cannot be classified or read.
    """
    p = Path(path)
    if not p.exists():
        raise ConverterError(f"Source not found: {p}")

    fmt = format if format else detect_format(p)
    if fmt not in {"agents_md", "skill_md", "agentskills", "crewai", "langgraph"}:
        raise ConverterError(f"Unknown format: {fmt}")

    if fmt == "agents_md":
        result = parse_agents_md(p)
    elif fmt == "skill_md":
        result = parse_skill_md(p)
    elif fmt == "crewai":
        result = parse_crewai(p)
    elif fmt == "langgraph":
        result = parse_langgraph(p)
    else:  # agentskills
        result = parse_agentskills(p)

    if use_llm:
        result.warnings.append(
            "LLM augmentation requested but not yet wired (F8); returning rule-based result."
        )
    return result


def parse_quickstart(answers: dict[str, str]) -> ParseResult:
    """Build a ParseResult from quickstart wizard answers.

    Each provided answer maps to a confidence of 1.0 with extractor="user".
    Answer keys: agent_name, agent_type, agent_description, non_negotiables,
    tools.

    Args:
        answers: Dict of free-form wizard answers.

    Returns:
        A ParseResult with format="quickstart".
    """
    intent = Intent()
    confidences: dict[str, float] = {}
    sources: dict[str, FieldSource] = {}
    warnings: list[str] = []

    raw_name = (answers.get("agent_name") or "").strip()
    raw_type = (answers.get("agent_type") or "").strip().lower()
    raw_desc = (answers.get("agent_description") or "").strip()

    intent.agent_name = _kebab_case(raw_name) if raw_name else "imported-agent"
    intent.agent_type = raw_type if raw_type in _VALID_AGENT_TYPES else "custom"
    intent.agent_description = raw_desc[:200] if raw_desc else "Imported via quickstart wizard"

    confidences["agent.name"] = 1.0
    confidences["agent.type"] = 1.0
    confidences["agent.description"] = 1.0
    sources["agent.name"] = FieldSource(extractor="user", snippet="quickstart")
    sources["agent.type"] = FieldSource(extractor="user", snippet="quickstart")
    sources["agent.description"] = FieldSource(extractor="user", snippet="quickstart")

    # Parse non-negotiables from comma-separated string
    raw_nn = (answers.get("non_negotiables") or "").strip()
    if raw_nn:
        for i, item in enumerate(raw_nn.split(",")):
            item = item.strip()
            if item:
                intent.non_negotiables.append(
                    NonNegotiable(rule=item, severity="hard")
                )
                key = f"intent.non_negotiables[{i}].rule"
                confidences[key] = 1.0
                sources[key] = FieldSource(extractor="user", snippet="quickstart")

    # Parse tools from comma-separated string
    raw_tools = (answers.get("tools") or "").strip()
    if raw_tools:
        for i, item in enumerate(raw_tools.split(",")):
            item = item.strip()
            if item:
                intent.tools_allowed.append(
                    ToolPermission(name=item, rationale="quickstart import")
                )
                key = f"intent.tools.allowed[{i}].name"
                confidences[key] = 1.0
                sources[key] = FieldSource(extractor="user", snippet="quickstart")

    return ParseResult(
        intent=intent,
        confidences=confidences,
        sources=sources,
        warnings=warnings,
        format="quickstart",
    )


def _stub_intent(name_seed: str, description: str | None = None) -> Intent:
    intent = Intent()
    intent.agent_name = _kebab_case(name_seed) or "imported-agent"
    intent.agent_type = "custom"
    intent.agent_description = description or f"Imported from {name_seed}"
    intent.agent_description = intent.agent_description[:200]
    return intent


def _kebab_case(text: str) -> str:
    """Convert text to kebab-case."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return ""
    if not text[0].isalpha():
        text = "x-" + text
    return text[:64]
