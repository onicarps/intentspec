"""Format detection — content-driven, not extension-driven.

`detect_format(path)` returns one of "agents_md", "skill_md", "agentskills"
or raises ConverterError when the input cannot be classified.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from intentspec.converter.types import ConverterError


_AGENTSKILLS_SUBDIRS = ("Resources", "Scripts", "References")


def detect_format(path: Path | str) -> str:
    """Detect the converter input format for `path`.

    Rules (per architecture §3.3):
      0. If `path` is a file named `crewai.yaml` or `crewai.yml` -> "crewai".
      1. If `path` is a directory containing `SKILL.md` plus any of
         `Resources/`, `Scripts/`, or `References/` -> "agentskills".
      2. If the primary file starts with a YAML frontmatter block (`^---\n`)
         that parses with `yaml.safe_load` and contains a `name` key -> "skill_md".
      3. If `path` is a markdown file (`.md` or unknown extension) -> "agents_md".
      4. Otherwise raise `ConverterError`.

    Args:
        path: File or directory path to classify.

    Returns:
        The detected format identifier.

    Raises:
        ConverterError: If the path does not exist or no rule matches.
    """
    p = Path(path)
    if not p.exists():
        raise ConverterError(f"Path does not exist: {p}")

    # CrewAI: file named crewai.yaml or crewai.yml
    if p.is_file() and p.stem.lower() == "crewai" and p.suffix.lower() in (".yaml", ".yml"):
        return "crewai"

    if p.is_dir():
        skill = p / "SKILL.md"
        if skill.is_file() and any((p / sub).is_dir() for sub in _AGENTSKILLS_SUBDIRS):
            return "agentskills"
        if skill.is_file():
            if _looks_like_skill_md(skill):
                return "skill_md"
            return "agentskills"
        raise ConverterError(
            f"Directory has no SKILL.md and no recognized agentskills layout: {p}"
        )

    if p.is_file():
        if _looks_like_skill_md(p):
            return "skill_md"
        return "agents_md"

    raise ConverterError(f"Unrecognized input: {p}")


def _looks_like_skill_md(path: Path) -> bool:
    """Return True iff the file begins with a YAML frontmatter block containing `name`."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            first = f.readline()
            if first.strip() != "---":
                return False
            buf: list[str] = []
            for line in f:
                if line.strip() == "---":
                    break
                buf.append(line)
            else:
                return False
        data = yaml.safe_load("".join(buf))
    except (OSError, yaml.YAMLError):
        return False
    return isinstance(data, dict) and "name" in data
