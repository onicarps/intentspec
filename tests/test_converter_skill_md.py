"""Tests for SKILL.md parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from intentspec.converter import parse
from intentspec.converter.skill_md import parse_skill_md
from intentspec.converter.types import ConverterError
from intentspec.spec.validate import validate_file

FIXTURES = Path(__file__).parent / "fixtures" / "sample_skills_md"


class TestParseSkillMd:
    """Test parse_skill_md() against fixture files."""

    def test_simple_frontmatter(self):
        r = parse_skill_md(FIXTURES / "simple.md")
        assert r.intent.agent_name == "changelog-writer"
        assert r.intent.agent_type == "custom"
        assert "release notes" in r.intent.agent_description.lower()
        assert r.format == "skill_md"

    def test_simple_constraints(self):
        r = parse_skill_md(FIXTURES / "simple.md")
        assert len(r.intent.constraints) >= 3
        # MUST group entries → enforceable
        assert r.intent.constraints[0].enforceable is True
        # Prefer present tense → not enforceable
        soft = [c for c in r.intent.constraints if c.enforceable is False]
        assert len(soft) >= 1

    def test_simple_non_negotiables(self):
        r = parse_skill_md(FIXTURES / "simple.md")
        assert len(r.intent.non_negotiables) >= 1
        hard = [nn for nn in r.intent.non_negotiables if nn.severity == "hard"]
        assert len(hard) >= 1

    def test_simple_no_goals(self):
        """simple.md has Overview as paragraph, not bullets → no goals extracted."""
        r = parse_skill_md(FIXTURES / "simple.md")
        # Overview is a paragraph, not bullets, so no goals
        assert len(r.intent.goals) == 0

    def test_simple_metadata_tags(self):
        r = parse_skill_md(FIXTURES / "simple.md")
        assert "docs" in r.intent.metadata.tags
        assert "release-notes" in r.intent.metadata.tags
        assert "v0.3.1" in r.intent.metadata.tags

    def test_simple_confidences(self):
        r = parse_skill_md(FIXTURES / "simple.md")
        # Frontmatter fields should have 0.90 confidence
        assert r.confidences.get("agent.name", 0) >= 0.85
        assert r.confidences.get("agent.description", 0) >= 0.85

    def test_simple_sources(self):
        r = parse_skill_md(FIXTURES / "simple.md")
        assert "agent.name" in r.sources
        assert r.sources["agent.name"].extractor == "rule"

    def test_complex(self):
        r = parse_skill_md(FIXTURES / "complex.md")
        assert r.intent.agent_name
        assert r.intent.agent_description
        assert len(r.intent.constraints) > 0 or len(r.intent.non_negotiables) > 0

    def test_edge_no_frontmatter(self):
        with pytest.raises(ConverterError, match="does not begin with YAML frontmatter"):
            parse_skill_md(FIXTURES / "edge-no-frontmatter.md")

    def test_output_passes_validation(self):
        """Parsed output should produce a valid intent.yaml."""
        r = parse_skill_md(FIXTURES / "simple.md")
        # The intent should be schema-valid
        from intentspec.spec.validate import validate_schema
        data = r.intent.to_dict()
        errors = validate_schema(data)
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_parse_dispatch(self):
        """parse() should auto-detect skill_md format and dispatch."""
        r = parse(FIXTURES / "simple.md")
        assert r.format == "skill_md"
        assert r.intent.agent_name == "changelog-writer"

    def test_parse_with_format_override(self):
        """parse() with format='skill_md' should work even if auto-detect differs."""
        r = parse(FIXTURES / "simple.md", format="skill_md")
        assert r.format == "skill_md"
        assert r.intent.agent_name == "changelog-writer"

    def test_file_not_found(self):
        with pytest.raises(ConverterError):
            parse_skill_md("/nonexistent/path/SKILL.md")

    def test_unclosed_frontmatter(self):
        """SKILL.md with opening --- but no closing --- should raise."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\nname: test\nno closing frontmatter\n")
            f.flush()
            with pytest.raises(ConverterError, match="unclosed"):
                parse_skill_md(f.name)

    def test_empty_body(self):
        """SKILL.md with only frontmatter and no body sections."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\nname: empty-body-agent\n---\n")
            f.flush()
            r = parse_skill_md(f.name)
            assert r.intent.agent_name == "empty-body-agent"
            assert len(r.warnings) >= 1  # "No extractable agent rules"

    def test_utf8_bom(self):
        """SKILL.md with UTF-8 BOM should parse correctly."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".md", delete=False) as f:
            f.write(b"\xef\xbb\xbf---\nname: bom-agent\n---\n## Instructions\n- MUST do something\n")
            f.flush()
            r = parse_skill_md(f.name)
            assert r.intent.agent_name == "bom-agent"
