"""agentskills directory parser per architecture §4.3.

Parses an agentskills directory layout: SKILL.md + Resources/ Scripts/ References/.
"""

from __future__ import annotations

from pathlib import Path

from intentspec.converter.skill_md import parse_skill_md
from intentspec.converter.types import ConverterError, FieldSource, ParseResult
from intentspec.models.intent import ToolPermission

__all__ = ["parse_agentskills"]


def parse_agentskills(path: Path | str) -> ParseResult:
    """Parse an agentskills directory into a ParseResult.

    The directory must contain a SKILL.md file. Subdirectories Resources/,
    Scripts/, and References/ are scanned for additional tools and tags.

    Args:
        path: Path to the agentskills directory.

    Returns:
        ParseResult with extracted Intent, confidences, sources, and warnings.

    Raises:
        ConverterError: If the directory does not contain SKILL.md.
    """
    p = Path(path)
    if not p.is_dir():
        raise ConverterError(f"agentskills path is not a directory: {p}")

    skill_md = p / "SKILL.md"
    if not skill_md.is_file():
        raise ConverterError(f"agentskills directory missing SKILL.md: {p}")

    # Parse the SKILL.md using the existing parser
    result = parse_skill_md(skill_md)

    # Scan progressive disclosure directories
    _scan_progressive_disclosure(p, result)

    # Update format
    result.format = "agentskills"

    return result


def _scan_progressive_disclosure(directory: Path, result: ParseResult) -> None:
    """Scan Resources/, Scripts/, References/ for additional tools and tags."""
    # Scripts/ → tools.allowed
    scripts_dir = directory / "Scripts"
    if scripts_dir.is_dir():
        for script_file in sorted(scripts_dir.iterdir()):
            if script_file.is_file():
                tool_name = script_file.stem
                # Check for duplicates
                existing_names = {t.name.lower() for t in result.intent.tools_allowed}
                if tool_name.lower() not in existing_names:
                    idx = len(result.intent.tools_allowed)
                    result.intent.tools_allowed.append(
                        ToolPermission(name=tool_name, rationale="bundled script")
                    )
                    key = f"intent.tools.allowed[{idx}].name"
                    confidences = 0.80
                    result.confidences[key] = confidences
                    result.sources[key] = FieldSource(
                        line=None,
                        snippet=str(script_file.relative_to(directory)),
                        extractor="rule",
                    )

    # Resources/ → metadata.tags
    resources_dir = directory / "Resources"
    if resources_dir.is_dir():
        for resource_file in sorted(resources_dir.iterdir()):
            if resource_file.is_file():
                tag = resource_file.stem.replace("-", " ").replace("_", " ").lower()
                if tag not in result.intent.metadata.tags:
                    result.intent.metadata.tags.append(tag)

    # References/ → confidence boost (no new fields, just a marker)
    references_dir = directory / "References"
    if references_dir.is_dir():
        ref_files = list(references_dir.iterdir())
        if ref_files:
            result.warnings.append(
                f"References/ directory contains {len(ref_files)} file(s) — "
                "not yet used for extraction"
            )
