"""Tests for agentskills directory parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from intentspec.converter import parse
from intentspec.converter.agentskills import parse_agentskills
from intentspec.converter.types import ConverterError

FIXTURES = Path(__file__).parent / "fixtures" / "sample_agentskills"


class TestParseAgentskills:
    """Test parse_agentskills() against fixture directories."""

    def test_simple_directory(self):
        r = parse_agentskills(FIXTURES / "simple")
        assert r.format == "agentskills"
        assert r.intent.agent_name == "log-rotator"
        assert "ops" in r.intent.metadata.tags
        assert "logs" in r.intent.metadata.tags

    def test_simple_skills_parsed(self):
        """SKILL.md inside directory should be parsed."""
        r = parse_agentskills(FIXTURES / "simple")
        assert len(r.intent.constraints) >= 3
        assert len(r.intent.non_negotiables) >= 1

    def test_simple_tools_from_scripts(self):
        """Scripts/run.sh should be extracted as a tool."""
        r = parse_agentskills(FIXTURES / "simple")
        tool_names = {t.name.lower() for t in r.intent.tools_allowed}
        assert "run" in tool_names

    def test_complex_directory(self):
        r = parse_agentskills(FIXTURES / "complex")
        assert r.format == "agentskills"
        assert r.intent.agent_name == "dataset-validator"
        # Complex has Resources/ and References/ but no Scripts/
        # Resources should add tags
        assert any("data" in tag.lower() for tag in r.intent.metadata.tags)

    def test_complex_resources_as_tags(self):
        """Resources/ filenames should become tags."""
        r = parse_agentskills(FIXTURES / "complex")
        # Resources/data.json → tag "data"
        assert any("data" in tag.lower() for tag in r.intent.metadata.tags)

    def test_not_a_directory(self):
        with pytest.raises(ConverterError, match="not a directory"):
            parse_agentskills(FIXTURES / "simple/SKILL.md")

    def test_missing_skill_md(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(ConverterError, match="missing SKILL.md"):
                parse_agentskills(tmp)

    def test_parse_dispatch(self):
        """parse() should auto-detect agentskills format."""
        r = parse(FIXTURES / "simple")
        assert r.format == "agentskills"

    def test_output_passes_validation(self):
        """Parsed output should produce a valid intent.yaml."""
        from intentspec.spec.validate import validate_schema
        r = parse_agentskills(FIXTURES / "simple")
        data = r.intent.to_dict()
        errors = validate_schema(data)
        assert len(errors) == 0, f"Schema errors: {errors}"

    def test_references_warning(self):
        """References/ directory should produce a warning."""
        r = parse_agentskills(FIXTURES / "complex")
        ref_warnings = [w for w in r.warnings if "References" in w]
        assert len(ref_warnings) >= 1
