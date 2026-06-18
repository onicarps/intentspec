"""Public converter API: parse() and parse_quickstart()."""

from __future__ import annotations

import re
from pathlib import Path

from intentspec.converter.format_detect import detect_format
from intentspec.converter.types import ConverterError, FieldSource, ParseResult
from intentspec.models.intent import Intent


__all__ = [
    "parse",
    "parse_quickstart",
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
    if fmt not in {"agents_md", "skill_md", "agentskills"}:
        raise ConverterError(f"Unknown format: {fmt}")

    if fmt == "agents_md":
        result = _parse_agents_md_stub(p)
    elif fmt == "skill_md":
        result = _parse_skill_md_stub(p)
    else:
        result = _parse_agentskills_stub(p)

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


def _parse_agents_md_stub(path: Path) -> ParseResult:
    intent = _stub_intent(path.stem)
    confidences = {
        "agent.name": 0.50,
        "agent.type": 0.30,
        "agent.description": 0.30,
    }
    sources = {
        "agent.name": FieldSource(line=None, snippet=path.name, extractor="default"),
        "agent.type": FieldSource(extractor="default"),
        "agent.description": FieldSource(extractor="default"),
    }
    warnings = ["AGENTS.md parser is a stub; full extraction lands in F3."]
    return ParseResult(
        intent=intent,
        confidences=confidences,
        sources=sources,
        warnings=warnings,
        format="agents_md",
    )


def _parse_skill_md_stub(path: Path) -> ParseResult:
    intent = _stub_intent(path.stem)
    confidences = {
        "agent.name": 0.50,
        "agent.type": 0.30,
        "agent.description": 0.30,
    }
    sources = {
        "agent.name": FieldSource(line=None, snippet=path.name, extractor="default"),
        "agent.type": FieldSource(extractor="default"),
        "agent.description": FieldSource(extractor="default"),
    }
    warnings = ["SKILL.md parser is a stub; full extraction lands in F4."]
    return ParseResult(
        intent=intent,
        confidences=confidences,
        sources=sources,
        warnings=warnings,
        format="skill_md",
    )


def _parse_agentskills_stub(path: Path) -> ParseResult:
    intent = _stub_intent(path.name)
    confidences = {
        "agent.name": 0.50,
        "agent.type": 0.30,
        "agent.description": 0.30,
    }
    sources = {
        "agent.name": FieldSource(line=None, snippet=path.name, extractor="default"),
        "agent.type": FieldSource(extractor="default"),
        "agent.description": FieldSource(extractor="default"),
    }
    warnings = ["agentskills parser is a stub; full extraction lands in F5."]
    return ParseResult(
        intent=intent,
        confidences=confidences,
        sources=sources,
        warnings=warnings,
        format="agentskills",
    )


def _kebab_case(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return ""
    if not text[0].isalpha():
        text = "x-" + text
    return text[:64]
