"""Resolve agent source artifacts for an intent.yaml file."""

from __future__ import annotations

import re
from pathlib import Path

# Known source filenames, checked in priority order within intent.yaml's directory.
SOURCE_FILENAMES: tuple[str, ...] = (
    "AGENTS.md",
    "SKILL.md",
    "crewai.yaml",
    "crewai.yml",
    "langgraph.yaml",
    "langgraph.yml",
    "autogen-config.yaml",
    "autogen.yaml",
    "openai-agents.yaml",
    "openai_agents.yaml",
)

_SOURCE_HEADER_RE = re.compile(r"^#\s*Source:\s*(.+)\s*$")


def parse_source_from_header(intent_path: Path) -> Path | None:
    """Read ``# Source: ...`` provenance from the intent.yaml header."""
    try:
        lines = intent_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None

    for line in lines[:25]:
        m = _SOURCE_HEADER_RE.match(line.strip())
        if not m:
            continue
        raw = m.group(1).strip()
        raw_path = Path(raw)
        if raw_path.is_absolute():
            candidates = [raw_path]
        else:
            candidates = [
                intent_path.parent / raw,
                intent_path.parent / raw_path.name,
            ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
    return None


def find_sibling_source(intent_path: Path) -> Path | None:
    """Find a known source file beside intent.yaml."""
    parent = intent_path.parent
    for name in SOURCE_FILENAMES:
        candidate = parent / name
        if candidate.is_file():
            return candidate.resolve()

    if parent.is_dir():
        for child in sorted(parent.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                return (child / "SKILL.md").resolve()
    return None


def resolve_source_for_intent(intent_path: Path | str) -> Path | None:
    """Resolve the original agent spec for an intent.yaml.

    Resolution order:
    1. ``# Source:`` header comment written by ``intentspec init``
    2. Known sibling filenames (AGENTS.md, SKILL.md, framework configs, etc.)
    """
    path = Path(intent_path)
    if not path.is_file():
        return None

    header_source = parse_source_from_header(path)
    if header_source is not None:
        return header_source
    return find_sibling_source(path)


def is_orphaned(intent_path: Path | str) -> bool:
    """Return True when intent.yaml has no discoverable source artifact."""
    path = Path(intent_path)
    if not path.is_file():
        return False
    return resolve_source_for_intent(path) is None