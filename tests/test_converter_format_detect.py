"""Tests for converter/format_detect.py — content-driven format detection."""

from __future__ import annotations

import pytest

from intentspec.converter.format_detect import detect_format
from intentspec.converter.types import ConverterError


def test_detect_agents_md_for_plain_markdown(tmp_path):
    p = tmp_path / "AGENTS.md"
    p.write_text("# Coding Agent\n\nWhat we do.\n", encoding="utf-8")
    assert detect_format(p) == "agents_md"


def test_detect_agents_md_accepts_string_path(tmp_path):
    p = tmp_path / "AGENTS.md"
    p.write_text("# X\n", encoding="utf-8")
    assert detect_format(str(p)) == "agents_md"


def test_detect_agents_md_for_unknown_extension(tmp_path):
    p = tmp_path / "weird.txt"
    p.write_text("# Some agent\n", encoding="utf-8")
    assert detect_format(p) == "agents_md"


def test_detect_skill_md_with_frontmatter(tmp_path):
    p = tmp_path / "skill.md"
    p.write_text("---\nname: my-skill\ndescription: x\n---\n# Body\n", encoding="utf-8")
    assert detect_format(p) == "skill_md"


def test_detect_skill_md_requires_name_in_frontmatter(tmp_path):
    p = tmp_path / "skill.md"
    p.write_text("---\nversion: 1.0\n---\n# Body\n", encoding="utf-8")
    assert detect_format(p) == "agents_md"


def test_detect_skill_md_handles_bom(tmp_path):
    p = tmp_path / "skill.md"
    p.write_bytes(b"\xef\xbb\xbf---\nname: x\n---\n# Body\n")
    assert detect_format(p) == "skill_md"


def test_detect_agentskills_directory(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    (pkg / "Scripts").mkdir()
    assert detect_format(pkg) == "agentskills"


def test_detect_agentskills_with_resources(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    (pkg / "Resources").mkdir()
    assert detect_format(pkg) == "agentskills"


def test_detect_agentskills_with_references(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    (pkg / "References").mkdir()
    assert detect_format(pkg) == "agentskills"


def test_detect_directory_with_skill_md_only_falls_back_to_skill_md(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    assert detect_format(pkg) == "skill_md"


def test_detect_directory_without_skill_md_raises(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "Scripts").mkdir()
    with pytest.raises(ConverterError):
        detect_format(pkg)


def test_detect_missing_path_raises(tmp_path):
    with pytest.raises(ConverterError):
        detect_format(tmp_path / "missing")


def test_detect_skill_md_with_unterminated_frontmatter_falls_back(tmp_path):
    p = tmp_path / "broken.md"
    p.write_text("---\nname: x\nincomplete\n", encoding="utf-8")
    assert detect_format(p) == "agents_md"


def test_detect_skill_md_with_invalid_yaml_falls_back(tmp_path):
    p = tmp_path / "broken.md"
    p.write_text("---\n: : :\n---\n", encoding="utf-8")
    assert detect_format(p) == "agents_md"


def test_detect_agentskills_uses_real_fixtures():
    from pathlib import Path
    fixture_dir = Path(__file__).parent / "fixtures" / "sample_agentskills" / "simple"
    if fixture_dir.exists():
        assert detect_format(fixture_dir) == "agentskills"
