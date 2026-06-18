"""SKILL.md (agentskills) parser per architecture §4.2.

Parses YAML frontmatter + Markdown body sections from agentskills SKILL.md files.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from intentspec.converter.types import ConverterError, FieldSource, ParseResult
from intentspec.models.intent import (
    Constraint,
    Goal,
    Intent,
    NonNegotiable,
)

_RE_HARD_KW = re.compile(r"^(NEVER|MUST\s+NOT|DO\s+NOT|DON'T|MUST|REQUIRED\s+TO|ALWAYS)\b", re.IGNORECASE)
_RE_SOFT_KW = re.compile(r"^(prefer|should|may|can|could|might)\b", re.IGNORECASE)
_RE_BULLET = re.compile(r"^\s*[-*]\s+(.+)")
_RE_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.+)")
_RE_H2H3 = re.compile(r"^#{2,3}\s+(.+)")


def parse_skill_md(path: Path | str) -> ParseResult:
    """Parse a SKILL.md file into a ParseResult.

    Args:
        path: Path to the SKILL.md source file.

    Returns:
        ParseResult with extracted Intent, confidences, sources, and warnings.

    Raises:
        ConverterError: If the file cannot be read or frontmatter is invalid.
    """
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ConverterError(f"Cannot read {p}: {exc}") from exc

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split frontmatter and body
    frontmatter, body = _split_frontmatter(text, p)

    intent = Intent()
    confidences: dict[str, float] = {}
    sources: dict[str, FieldSource] = {}
    warnings: list[str] = []

    # Parse frontmatter
    fm_name = frontmatter.get("name", "")
    if not fm_name:
        raise ConverterError(f"SKILL.md at {p} is missing required 'name' in frontmatter")

    intent.agent_name = str(fm_name).strip()
    confidences["agent.name"] = 0.90
    sources["agent.name"] = FieldSource(line=2, snippet=str(fm_name), extractor="rule")

    if "description" in frontmatter and frontmatter["description"]:
        desc = str(frontmatter["description"]).strip()
        # Truncate to 200 chars at sentence boundary
        if len(desc) > 200:
            desc = _truncate_sentence(desc, 200)
        intent.agent_description = desc
        confidences["agent.description"] = 0.90
        sources["agent.description"] = FieldSource(
            line=_find_fm_line(text, "description"),
            snippet=desc[:60],
            extractor="rule",
        )

    intent.agent_type = "custom"
    confidences["agent.type"] = 0.30
    sources["agent.type"] = FieldSource(extractor="default", snippet="inferred")

    # Parse version and tags from frontmatter
    if "version" in frontmatter:
        version = str(frontmatter["version"]).strip()
        if not intent.metadata.tags:
            intent.metadata.tags = []
        intent.metadata.tags.append(f"v{version}")
        confidences["metadata.tags"] = 0.90
        sources["metadata.tags"] = FieldSource(
            line=_find_fm_line(text, "version"),
            snippet=version,
            extractor="rule",
        )

    if "tags" in frontmatter and isinstance(frontmatter["tags"], list):
        for tag in frontmatter["tags"]:
            tag_str = str(tag).strip()
            if tag_str not in intent.metadata.tags:
                intent.metadata.tags.append(tag_str)

    # Parse body sections
    sections = _split_sections(body)

    for title, start, section_body in sections:
        tl = title.lower().strip()

        if tl in ("overview", "description"):
            # First paragraph or bullet → first goal
            bullets = _extract_bullets(section_body)
            if bullets:
                first_text = bullets[0][0]
                intent.goals.append(Goal(description=first_text[:200], priority="medium"))
                key = "intent.goals[0].description"
                confidences[key] = 0.70
                sources[key] = FieldSource(
                    line=start + bullets[0][1],
                    snippet=first_text[:60],
                    extractor="rule",
                )

        elif tl == "goals":
            bullets = _extract_bullets(section_body)
            for j, (item_text, item_line) in enumerate(bullets):
                intent.goals.append(Goal(description=item_text[:200], priority="medium"))
                key = f"intent.goals[{j}].description"
                confidences[key] = 0.70
                sources[key] = FieldSource(
                    line=start + item_line,
                    snippet=item_text[:60],
                    extractor="rule",
                )

        elif tl == "instructions":
            bullets = _extract_bullets(section_body)
            for k, (item_text, item_line) in enumerate(bullets):
                m_hard = _RE_HARD_KW.match(item_text)
                m_soft = _RE_SOFT_KW.match(item_text)
                enforceable = True
                conf_val = 0.55
                if m_hard:
                    enforceable = True
                    conf_val = 0.85
                elif m_soft:
                    enforceable = False
                    conf_val = 0.55
                intent.constraints.append(Constraint(rule=item_text[:500], enforceable=enforceable))
                key = f"intent.constraints[{k}].rule"
                confidences[key] = conf_val
                sources[key] = FieldSource(
                    line=start + item_line,
                    snippet=item_text[:60],
                    extractor="rule",
                )

        elif tl in ("notes", "important", "caveats"):
            bullets = _extract_bullets(section_body)
            for k, (item_text, item_line) in enumerate(bullets):
                severity = "hard"
                if _RE_SOFT_KW.match(item_text) and not _RE_HARD_KW.match(item_text):
                    severity = "soft"
                intent.non_negotiables.append(
                    NonNegotiable(rule=item_text[:500], severity=severity)
                )
                key = f"intent.non_negotiables[{k}].rule"
                confidences[key] = 0.70
                sources[key] = FieldSource(
                    line=start + item_line,
                    snippet=item_text[:60],
                    extractor="rule",
                )

    if not intent.goals and not intent.constraints and not intent.non_negotiables:
        warnings.append("No extractable agent rules found in SKILL.md body")

    return ParseResult(
        intent=intent,
        confidences=confidences,
        sources=sources,
        warnings=warnings,
        format="skill_md",
    )


def _split_frontmatter(text: str, path: Path) -> tuple[dict, str]:
    """Split SKILL.md text into (frontmatter_dict, body_text).

    Raises ConverterError if frontmatter is missing or malformed.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ConverterError(
            f"SKILL.md at {path} does not begin with YAML frontmatter (---)"
        )

    # Find closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        raise ConverterError(
            f"SKILL.md at {path} has unclosed YAML frontmatter"
        )

    fm_text = "\n".join(lines[1:end_idx])
    body = "\n".join(lines[end_idx + 1:])

    try:
        data = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise ConverterError(
            f"SKILL.md at {path} has invalid YAML frontmatter: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ConverterError(
            f"SKILL.md at {path} frontmatter is not a YAML mapping"
        )

    return data, body


def _find_fm_line(text: str, key: str) -> int | None:
    """Find 1-based line number of a key in YAML frontmatter."""
    for i, line in enumerate(text.split("\n"), 1):
        if line.strip().startswith(f"{key}:"):
            return i
    return None


def _split_sections(body: str) -> list[tuple[str, int, list[str]]]:
    """Split Markdown body into (title, start_line, body_lines) tuples."""
    sections: list[tuple[str, int, list[str]]] = []
    cur_title: str | None = None
    cur_start: int | None = None
    cur_body: list[str] = []
    fence = False

    for i, line in enumerate(body.split("\n")):
        stripped = line.strip()
        if stripped.startswith("```"):
            fence = not fence
        if not fence:
            m = _RE_H2H3.match(line)
            if m:
                if cur_title is not None:
                    sections.append((cur_title, cur_start or 0, cur_body))
                cur_title = m.group(1).strip()
                cur_start = i + 1
                cur_body = []
                continue
        cur_body.append(line)

    if cur_title is not None:
        sections.append((cur_title, cur_start or 0, cur_body))

    return sections


def _extract_bullets(lines: list[str]) -> list[tuple[str, int]]:
    """Extract bullet/numbered items from lines. Returns [(text, line_offset)]."""
    items: list[tuple[str, int]] = []
    for i, line in enumerate(lines):
        m = _RE_BULLET.match(line)
        if m:
            items.append((m.group(1).strip(), i))
            continue
        m = _RE_NUMBERED.match(line)
        if m:
            items.append((m.group(1).strip(), i))
    return items


def _truncate_sentence(text: str, limit: int) -> str:
    """Truncate text at sentence boundary within limit."""
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    for pos in range(min(limit, len(text)) - 1, -1, -1):
        if text[pos] in ".!?":
            return text[:pos + 1]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space]
    return truncated
