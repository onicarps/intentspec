"""Rule-based AGENTS.md parser per architecture §4.1.

Fully deterministic: same input always yields byte-identical output.
Handles edge cases (empty, BOM, non-English, malformed, recursive refs).
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from intentspec.converter.types import ConverterError, FieldSource, ParseResult
from intentspec.models.intent import (
    Boundary,
    Constraint,
    Goal,
    Intent,
    NonNegotiable,
    ToolPermission,
)

__all__ = ["parse_agents_md"]

_GOALS_TITLES = frozenset({"goals", "purpose", "what you do", "mission", "objectives"})
_CONSTRAINTS_TITLES = frozenset({"constraints"})
_NON_NEGOTIABLES_TITLES = frozenset({"non-negotiables", "hard rules"})
_BOUNDARIES_TITLES = frozenset({"boundaries", "scope", "limitations", "out of scope"})
_TOOLS_TITLES = frozenset({"tools", "tech stack", "allowed tools"})

_EMPHATIC_PATTERNS = [
    re.compile(r"under no circumstances", re.IGNORECASE),
    re.compile(r"never ever", re.IGNORECASE),
    re.compile(r"absolutely never", re.IGNORECASE),
    re.compile(r"strictly forbidden", re.IGNORECASE),
]

_RE_HARD_KW = re.compile(r"^(NEVER|MUST\s+NOT|DO\s+NOT|DON'T|MUST|REQUIRED\s+TO|ALWAYS)\b", re.IGNORECASE)
_RE_SOFT_KW = re.compile(r"^(prefer|should|may|can|could|might)\b", re.IGNORECASE)
_RE_CODE_SPAN = re.compile(r"`([^`]+)`")
_RE_TABLE_TOOL_HEADER = re.compile(r"^\|?\s*(tool|component|library)", re.IGNORECASE)
_RE_TABLE_ROW = re.compile(r"^\|\s*(?P<name>[^|]+)\s*\|\s*(?P<rest>.+)")
_RE_SEE_ALSO = re.compile(r"see\s+also\s*:\s*(.+)", re.IGNORECASE)
_RE_H1 = re.compile(r"^#\s+(.+)$")
_RE_H2H3 = re.compile(r"^#{2,3}\s+(.+)$")
_RE_BULLET = re.compile(r"^\s*[-*]\s+(.+)")
_RE_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.+)")
_RE_INTRO_VERB = re.compile(r"^(run|use|execute|call|invoke)\s+", re.IGNORECASE)
_RE_ENGLISH_KW = re.compile(
    r"\b(never|must\s+not|do\s+not|don't|must|required\s+to|always|prefer|should|may|can|could|might)\b",
    re.IGNORECASE,
)


def parse_agents_md(path: Path | str) -> ParseResult:
    """Parse an AGENTS.md file into a ParseResult.

    Args:
        path: Path to the AGENTS.md source file.

    Returns:
        A ParseResult with the extracted Intent plus per-field
        confidences, sources, and any extraction warnings.

    Raises:
        ConverterError: If the file cannot be read.
    """
    p = Path(path)
    result = _parse_single(p, follow_refs=False)
    result = _follow_and_merge(result, p)
    return result


def _parse_single(p: Path, *, follow_refs: bool = False) -> ParseResult:
    try:
        raw_bytes = p.read_bytes()
    except OSError as exc:
        raise ConverterError(f"Cannot read {p}: {exc}") from exc

    if not raw_bytes:
        return _empty_result(p)

    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw_bytes.decode("utf-8-sig", errors="replace")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    intent = Intent()
    confidences: dict[str, float] = {}
    sources: dict[str, FieldSource] = {}
    warnings: list[str] = []

    h1_line, h1_text = _find_h1(lines)
    name, name_conf, name_src = _extract_name(h1_text, h1_line, p)
    intent.agent_name = name
    confidences["agent.name"] = name_conf
    sources["agent.name"] = name_src

    desc, desc_conf, desc_src = _extract_description(lines, h1_line)
    intent.agent_description = desc
    confidences["agent.description"] = desc_conf
    sources["agent.description"] = desc_src

    intent.agent_type = "custom"
    confidences["agent.type"] = 0.30
    sources["agent.type"] = FieldSource(extractor="default", snippet="inferred")

    sections = _split_sections(lines)
    is_non_eng = _is_non_english(lines)

    goals, g_confs, g_srcs, g_warn = _extract_goals(sections, is_non_eng)
    intent.goals = goals
    confidences.update(g_confs)
    sources.update(g_srcs)
    if g_warn:
        warnings.append(g_warn)

    nn_items, nn_confs, nn_srcs = _extract_non_negotiables(sections, is_non_eng)
    nn_rules_lower = {nn.rule.strip().lower() for nn in nn_items}

    constraints, c_confs, c_srcs = _extract_constraints(sections, nn_rules_lower, is_non_eng)
    intent.constraints = constraints
    confidences.update(c_confs)
    sources.update(c_srcs)

    intent.non_negotiables = nn_items
    confidences.update(nn_confs)
    sources.update(nn_srcs)

    tools, t_confs, t_srcs = _extract_tools(sections, lines)
    intent.tools_allowed = tools
    confidences.update(t_confs)
    sources.update(t_srcs)

    boundaries, b_confs, b_srcs = _extract_boundaries(sections, is_non_eng)
    intent.boundaries = boundaries
    confidences.update(b_confs)
    sources.update(b_srcs)

    if is_non_eng:
        has_extracted = bool(intent.constraints or intent.non_negotiables or intent.goals)
        if not has_extracted:
            msg = "No extractable agent rules in source language"
            if msg not in warnings:
                warnings.append(msg)

    if follow_refs:
        result = ParseResult(
            intent=intent, confidences=confidences, sources=sources,
            warnings=warnings, format="agents_md",
        )
        return _follow_and_merge(result, p)

    return ParseResult(
        intent=intent, confidences=confidences, sources=sources,
        warnings=warnings, format="agents_md",
    )


def _follow_and_merge(result: ParseResult, source_path: Path) -> ParseResult:
    """Follow See-also references up to depth 2 and merge into result."""
    lines = source_path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    refs = _find_references(lines, source_path)
    if not refs:
        return result

    visited: set[str] = {str(source_path.resolve())}
    queue: list[tuple[Path, int]] = [(r, 1) for r in refs]

    while queue:
        ref_path, depth = queue.pop(0)
        resolved = str(ref_path.resolve())
        if resolved in visited:
            continue
        visited.add(resolved)
        if depth > 2:
            if not any("depth limit" in w for w in result.warnings):
                result.warnings.append("Recursive reference depth limit reached; deeper references not followed")
            continue

        try:
            sub = _parse_single(ref_path, follow_refs=False)
        except ConverterError:
            continue

        for w in sub.warnings:
            if w not in result.warnings:
                result.warnings.append(w)

        reduction = 0.10 * depth
        _merge_fields(sub, result, reduction, ref_path)

        if depth < 2:
            sub_lines = ref_path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n").split("\n")
            sub_refs = _find_references(sub_lines, ref_path)
            for sr in sub_refs:
                sr_resolved = str(sr.resolve())
                if sr_resolved not in visited:
                    queue.append((sr, depth + 1))

    return result


def _find_references(lines: list[str], source_path: Path) -> list[Path]:
    refs: list[Path] = []
    base_dir = source_path.parent
    for line in lines:
        m = _RE_SEE_ALSO.match(line.strip())
        if m:
            for ref_name in re.split(r"[,;]", m.group(1)):
                ref_name = ref_name.strip()
                if not ref_name:
                    continue
                ref_path = base_dir / ref_name
                if ref_path.is_file():
                    refs.append(ref_path)
    return refs


def _merge_fields(
    sub: ParseResult, result: ParseResult,
    reduction: float, ref_path: Path,
) -> None:
    intent = result.intent
    confs = result.confidences
    srcs = result.sources

    for si, g in enumerate(sub.intent.goals):
        if any(e.description.strip().lower() == g.description.strip().lower() for e in intent.goals):
            continue
        idx = len(intent.goals)
        intent.goals.append(Goal(description=g.description, priority=g.priority))
        base = sub.confidences.get(f"intent.goals[{si}].description", 0.80)
        confs[f"intent.goals[{idx}].description"] = max(0.0, round(base - reduction, 2))
        srcs[f"intent.goals[{idx}].description"] = FieldSource(snippet=f"via {ref_path.name}", extractor="rule")
        confs[f"intent.goals[{idx}].priority"] = max(0.0, round(0.80 - reduction, 2))
        srcs[f"intent.goals[{idx}].priority"] = FieldSource(extractor="rule")

    for si, c in enumerate(sub.intent.constraints):
        if any(e.rule.strip().lower() == c.rule.strip().lower() for e in intent.constraints):
            continue
        idx = len(intent.constraints)
        intent.constraints.append(Constraint(rule=c.rule, enforceable=c.enforceable))
        base = sub.confidences.get(f"intent.constraints[{si}].rule", 0.85 if c.enforceable else 0.55)
        confs[f"intent.constraints[{idx}].rule"] = max(0.0, round(base - reduction, 2))
        srcs[f"intent.constraints[{idx}].rule"] = FieldSource(snippet=f"via {ref_path.name}", extractor="rule")
        confs[f"intent.constraints[{idx}].enforceable"] = max(0.0, round(base - reduction, 2))
        srcs[f"intent.constraints[{idx}].enforceable"] = FieldSource(extractor="rule")

    for si, nn in enumerate(sub.intent.non_negotiables):
        if any(e.rule.strip().lower() == nn.rule.strip().lower() for e in intent.non_negotiables):
            continue
        idx = len(intent.non_negotiables)
        intent.non_negotiables.append(NonNegotiable(rule=nn.rule, severity=nn.severity))
        confs[f"intent.non_negotiables[{idx}].rule"] = max(0.0, round(0.80 - reduction, 2))
        srcs[f"intent.non_negotiables[{idx}].rule"] = FieldSource(snippet=f"via {ref_path.name}", extractor="rule")
        confs[f"intent.non_negotiables[{idx}].severity"] = max(0.0, round(0.80 - reduction, 2))
        srcs[f"intent.non_negotiables[{idx}].severity"] = FieldSource(extractor="rule")

    for si, t in enumerate(sub.intent.tools_allowed):
        if any(e.name.strip().lower() == t.name.strip().lower() for e in intent.tools_allowed):
            continue
        idx = len(intent.tools_allowed)
        intent.tools_allowed.append(ToolPermission(name=t.name, rationale=t.rationale))
        base = sub.confidences.get(f"intent.tools.allowed[{si}].name", 0.85)
        confs[f"intent.tools.allowed[{idx}].name"] = max(0.0, round(base - reduction, 2))
        srcs[f"intent.tools.allowed[{idx}].name"] = FieldSource(snippet=f"via {ref_path.name}", extractor="rule")
        confs[f"intent.tools.allowed[{idx}].rationale"] = max(0.0, round(base - reduction, 2))
        srcs[f"intent.tools.allowed[{idx}].rationale"] = FieldSource(extractor="rule")

    for si, b in enumerate(sub.intent.boundaries):
        if any(e.scope.strip().lower() == b.scope.strip().lower() for e in intent.boundaries):
            continue
        idx = len(intent.boundaries)
        intent.boundaries.append(Boundary(scope=b.scope, out_of_scope=b.out_of_scope))
        confs[f"intent.boundaries[{idx}].scope"] = max(0.0, round(0.75 - reduction, 2))
        srcs[f"intent.boundaries[{idx}].scope"] = FieldSource(snippet=f"via {ref_path.name}", extractor="rule")
        confs[f"intent.boundaries[{idx}].out_of_scope"] = max(0.0, round(0.75 - reduction, 2))
        srcs[f"intent.boundaries[{idx}].out_of_scope"] = FieldSource(extractor="rule")


def _empty_result(path: Path) -> ParseResult:
    intent = Intent()
    intent.agent_name = _kebab_case(path.stem) or "imported-agent"
    intent.agent_description = "<empty source>"
    return ParseResult(
        intent=intent,
        confidences={"agent.name": 0.50, "agent.type": 0.0, "agent.description": 0.0},
        sources={
            "agent.name": FieldSource(extractor="default", snippet=path.name),
            "agent.type": FieldSource(extractor="default"),
            "agent.description": FieldSource(extractor="default"),
        },
        warnings=["Source file is empty"],
        format="agents_md",
    )


def _find_h1(lines: list[str]) -> tuple[int | None, str]:
    for i, line in enumerate(lines):
        m = _RE_H1.match(line)
        if m:
            return i + 1, m.group(1).strip()
    return None, ""


def _extract_name(
    h1_text: str, h1_line: int | None, path: Path
) -> tuple[str, float, FieldSource]:
    if h1_text:
        cleaned = re.sub(r"^you\s+are\s+(a\s+|an\s+)?", "", h1_text, flags=re.IGNORECASE)
        name = _kebab_case(cleaned)
        if name:
            return name, 0.85, FieldSource(line=h1_line, snippet=h1_text, extractor="rule")
    stem = _kebab_case(path.stem)
    return stem or "imported-agent", 0.50, FieldSource(line=None, snippet=path.name, extractor="default")


def _extract_description(
    lines: list[str], h1_line: int | None,
) -> tuple[str, float, FieldSource]:
    start = h1_line if h1_line is not None else 0
    para: list[str] = []
    para_start: int | None = None
    for i in range(start, len(lines)):
        line = lines[i].strip()
        if not line:
            if para:
                break
            continue
        if line.startswith("#"):
            break
        if line.startswith("```"):
            break
        if line.startswith("|") or _RE_SEE_ALSO.match(line):
            break
        if para_start is None:
            para_start = i + 1
        para.append(line)

    if not para:
        return "<no description>", 0.30, FieldSource(extractor="default")

    full = " ".join(para)
    desc, _ = _truncate_sentence(full, 200)
    return desc, 0.80, FieldSource(line=para_start, snippet=full[:80], extractor="rule")


def _truncate_sentence(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    for pos in range(min(limit, len(text)) - 1, -1, -1):
        if text[pos] in ".!?":
            return text[: pos + 1], True
    last_space = text[:limit].rfind(" ")
    if last_space > 0:
        return text[:last_space], True
    return text[:limit], True


def _split_sections(lines: list[str]) -> list[tuple[str, int, list[str]]]:
    sections: list[tuple[str, int, list[str]]] = []
    cur_title: str | None = None
    cur_start: int | None = None
    cur_body: list[str] = []
    in_code_fence = False

    def _flush():
        if cur_title is not None:
            sections.append((cur_title, cur_start or 0, cur_body))

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
        if in_code_fence and _RE_H2H3.match(line):
            in_code_fence = False
        if not in_code_fence:
            m = _RE_H2H3.match(line)
            if m:
                _flush()
                cur_title = m.group(1).strip()
                cur_start = i + 1
                cur_body = []
                continue
        cur_body.append(line)
    _flush()
    return sections


def _extract_goals(
    sections: list[tuple[str, int, list[str]]], is_non_eng: bool
) -> tuple[list[Goal], dict[str, float], dict[str, FieldSource], str]:
    if is_non_eng:
        return [], {}, {}, "No extractable agent rules in source language"

    goals: list[Goal] = []
    confidences: dict[str, float] = {}
    sources: dict[str, FieldSource] = {}
    warning = ""

    for title, start, body in sections:
        if title.lower().strip() in _GOALS_TITLES:
            for j, (item_text, item_line) in enumerate(_extract_bullets(body)):
                goals.append(Goal(description=item_text, priority="medium"))
                key = f"intent.goals[{j}].description"
                confidences[key] = 0.80
                sources[key] = FieldSource(
                    line=(start + item_line) if item_line else None,
                    snippet=item_text[:60], extractor="rule",
                )
                key2 = f"intent.goals[{j}].priority"
                confidences[key2] = 0.80
                sources[key2] = FieldSource(extractor="rule", snippet="medium")
            break

    if not goals:
        warning = "No explicit goals section found"

    return goals, confidences, sources, warning


def _extract_constraints(
    sections: list[tuple[str, int, list[str]]],
    nn_rules_lower: set[str],
    is_non_eng: bool,
) -> tuple[list[Constraint], dict[str, float], dict[str, FieldSource]]:
    if is_non_eng:
        return [], {}, {}

    constraints: list[Constraint] = []
    confidences: dict[str, float] = {}
    sources: dict[str, FieldSource] = {}
    seen: set[str] = set()

    def _add(rule_text: str, enforceable: bool, line: int | None, conf_val: float):
        dedup = re.sub(r"\s+", " ", rule_text.strip().lower())
        if dedup in seen or dedup in nn_rules_lower:
            return
        seen.add(dedup)
        idx = len(constraints)
        constraints.append(Constraint(rule=rule_text, enforceable=enforceable))
        key = f"intent.constraints[{idx}].rule"
        confidences[key] = conf_val
        sources[key] = FieldSource(line=line, snippet=rule_text[:60], extractor="rule")
        key2 = f"intent.constraints[{idx}].enforceable"
        confidences[key2] = conf_val
        sources[key2] = FieldSource(extractor="rule")

    for title, start, body in sections:
        if title.lower().strip() in _CONSTRAINTS_TITLES:
            for item_text, item_line_off in _extract_bullets(body):
                if _RE_HARD_KW.match(item_text):
                    _add(item_text, True, (start + item_line_off) if item_line_off else None, 0.85)
                elif _RE_SOFT_KW.match(item_text):
                    _add(item_text, False, (start + item_line_off) if item_line_off else None, 0.55)

    return constraints, confidences, sources


def _extract_non_negotiables(
    sections: list[tuple[str, int, list[str]]],
    is_non_eng: bool,
) -> tuple[list[NonNegotiable], dict[str, float], dict[str, FieldSource]]:
    if is_non_eng:
        return [], {}, {}

    non_negs: list[NonNegotiable] = []
    confidences: dict[str, float] = {}
    sources: dict[str, FieldSource] = {}
    seen: set[str] = set()

    def _add(rule: str, severity: str, line: int | None):
        dedup = re.sub(r"\s+", " ", rule.strip().lower())
        if dedup in seen:
            return
        seen.add(dedup)
        idx = len(non_negs)
        non_negs.append(NonNegotiable(rule=rule, severity=severity))
        key = f"intent.non_negotiables[{idx}].rule"
        confidences[key] = 0.80
        sources[key] = FieldSource(line=line, snippet=rule[:60], extractor="rule")
        key2 = f"intent.non_negotiables[{idx}].severity"
        confidences[key2] = 0.80
        sources[key2] = FieldSource(extractor="rule")

    for title, start, body in sections:
        if title.lower().strip() in _NON_NEGOTIABLES_TITLES:
            for item_text, item_line_off in _extract_bullets(body):
                _add(item_text, "hard", (start + item_line_off) if item_line_off else None)

    for title, start, body in sections:
        tl = title.lower().strip()
        if tl in _NON_NEGOTIABLES_TITLES or tl in _CONSTRAINTS_TITLES:
            continue
        for item_text, item_line_off in _extract_bullets(body):
            for pat in _EMPHATIC_PATTERNS:
                if pat.search(item_text):
                    _add(item_text, "hard", (start + item_line_off) if item_line_off else None)
                    break

    for title, start, body in sections:
        tl = title.lower().strip()
        if tl in _CONSTRAINTS_TITLES or tl in _NON_NEGOTIABLES_TITLES:
            continue
        for item_text, item_line_off in _extract_bullets(body):
            if _RE_HARD_KW.match(item_text):
                dedup = re.sub(r"\s+", " ", item_text.strip().lower())
                if dedup not in seen:
                    _add(item_text, "hard", (start + item_line_off) if item_line_off else None)

    return non_negs, confidences, sources


def _extract_tools(
    sections: list[tuple[str, int, list[str]]],
    lines: list[str],
) -> tuple[list[ToolPermission], dict[str, float], dict[str, FieldSource]]:
    tools: list[ToolPermission] = []
    confidences: dict[str, float] = {}
    sources: dict[str, FieldSource] = {}
    seen_names: set[str] = set()

    def _add(name: str, rationale: str, conf: float, line: int | None):
        name = name.strip()
        if not name or name.lower() in seen_names:
            return
        seen_names.add(name.lower())
        rationale = rationale.strip() or "extracted from source"
        idx = len(tools)
        tools.append(ToolPermission(name=name, rationale=rationale))
        key = f"intent.tools.allowed[{idx}].name"
        confidences[key] = conf
        sources[key] = FieldSource(line=line, snippet=name, extractor="rule")
        key2 = f"intent.tools.allowed[{idx}].rationale"
        confidences[key2] = conf
        sources[key2] = FieldSource(line=line, snippet=rationale[:60], extractor="rule")

    for title, start, body in sections:
        if title.lower().strip() in _TOOLS_TITLES:
            in_table = False
            for j, bline in enumerate(body):
                bl = bline.strip()
                if not bl:
                    continue
                if bl.startswith("|"):
                    if re.match(r"^\|[\s\-:|]+\|$", bl):
                        continue
                    if _RE_TABLE_TOOL_HEADER.match(bl.replace("-", "")):
                        in_table = True
                        continue
                    if in_table:
                        m = _RE_TABLE_ROW.match(bl)
                        if m:
                            tname = m.group("name").strip().strip("`")
                            if re.match(r"^[\s\-:|]+$", tname):
                                continue
                            rest = m.group("rest")
                            rationale = _extract_rationale_from_table_row(rest)
                            _add(tname, rationale, 0.85, start + j + 1)
                    continue
                else:
                    in_table = False
                bullet = _strip_bullet(bl)
                if bullet:
                    tool_name, rationale_text = _extract_tool_from_prose(bullet)
                    if tool_name:
                        _add(tool_name, rationale_text, 0.65, start + j + 1)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("-"):
            continue
        m_intro = _RE_INTRO_VERB.match(stripped)
        if m_intro:
            rest = stripped[m_intro.end():]
            for m in _RE_CODE_SPAN.finditer(rest):
                code = m.group(1).strip()
                if not code or len(code) >= 40:
                    continue
                if " " in code:
                    code = code.split()[0]
                rationale = f"mentioned in source line {i + 1}"
                _add(code, rationale, 0.65, i + 1)

    return tools, confidences, sources


def _extract_rationale_from_table_row(rest: str) -> str:
    for cell in re.split(r"\|", rest):
        c = cell.strip()
        if c:
            return c
    return ""


def _extract_tool_from_prose(text: str) -> tuple[str, str]:
    for m in _RE_CODE_SPAN.finditer(text):
        code = m.group(1).strip()
        if code and len(code) < 40 and not code.startswith("http"):
            rationale = text.replace(m.group(0), code).strip()
            return code, rationale
    return "", ""


def _extract_boundaries(
    sections: list[tuple[str, int, list[str]]],
    is_non_eng: bool,
) -> tuple[list[Boundary], dict[str, float], dict[str, FieldSource]]:
    if is_non_eng:
        return [], {}, {}

    boundaries: list[Boundary] = []
    confidences: dict[str, float] = {}
    sources: dict[str, FieldSource] = {}
    in_scope_items: list[tuple[str, int | None]] = []
    out_scope_items: list[tuple[str, int | None]] = []

    for title, start, body in sections:
        tl = title.lower().strip()
        if tl in _BOUNDARIES_TITLES:
            is_oos_section = "out of scope" in tl
            is_is_section = tl == "scope"
            for item_text, item_line_off in _extract_bullets(body):
                low = item_text.lower().strip()
                line_num = (start + item_line_off) if item_line_off else None
                if low.startswith("out of scope") or low.startswith("fuera del alcance"):
                    text = re.sub(r"^out\s+of\s+scope\s*:\s*", "", item_text, flags=re.IGNORECASE)
                    text = re.sub(r"^fuera\s+del\s+alcance\s*:\s*", "", text, flags=re.IGNORECASE)
                    out_scope_items.append((text, line_num))
                elif low.startswith("in scope") or low.startswith("dentro del alcance"):
                    text = re.sub(r"^in\s+scope\s*:\s*", "", item_text, flags=re.IGNORECASE)
                    in_scope_items.append((text, line_num))
                elif is_oos_section:
                    out_scope_items.append((item_text, line_num))
                elif is_is_section:
                    in_scope_items.append((item_text, line_num))
                else:
                    in_scope_items.append((item_text, line_num))

    max_pairs = max(len(in_scope_items), len(out_scope_items))
    for idx in range(max_pairs):
        in_s = in_scope_items[idx][0] if idx < len(in_scope_items) else ""
        in_line = in_scope_items[idx][1] if idx < len(in_scope_items) else None
        out_s = out_scope_items[idx][0] if idx < len(out_scope_items) else ""
        out_line = out_scope_items[idx][1] if idx < len(out_scope_items) else None
        if not in_s and not out_s:
            continue
        if not in_s and out_s:
            in_s = "Agent's primary domain (see description)"
        boundaries.append(Boundary(scope=in_s, out_of_scope=out_s))
        key = f"intent.boundaries[{len(boundaries) - 1}].scope"
        confidences[key] = 0.75 if in_scope_items else 0.50
        sources[key] = FieldSource(line=in_line, snippet=in_s[:60], extractor="rule")
        key2 = f"intent.boundaries[{len(boundaries) - 1}].out_of_scope"
        confidences[key2] = 0.75
        sources[key2] = FieldSource(line=out_line, snippet=out_s[:60], extractor="rule")

    return boundaries, confidences, sources


def _extract_bullets(body: list[str]) -> list[tuple[str, int | None]]:
    items: list[tuple[str, int | None]] = []
    in_code_fence = False
    for i, line in enumerate(body):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            if _RE_H2H3.match(line):
                in_code_fence = False
            else:
                continue
        if stripped.startswith("#"):
            continue
        bullet = _strip_bullet(stripped)
        if bullet:
            items.append((bullet, i + 1))
    return items


def _strip_bullet(line: str) -> str:
    m = _RE_BULLET.match(line)
    if m:
        return m.group(1).strip()
    m = _RE_NUMBERED.match(line)
    if m:
        return m.group(1).strip()
    return ""


def _is_non_english(lines: list[str]) -> bool:
    english_kw = 0
    total = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("```"):
            continue
        total += 1
        if _RE_ENGLISH_KW.search(stripped):
            english_kw += 1
    if total == 0:
        return False
    return english_kw / total < 0.15


def _kebab_case(text: str) -> str:
    text = text.strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    if not text:
        return ""
    if not text[0].isalpha():
        text = "x-" + text
    return text[:64]
