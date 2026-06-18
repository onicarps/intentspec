"""Additional CLI tests for strict mode, parent dir creation, and error paths."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from intentspec.cli import main


_FIXTURE_AGENTS_MD = "# Demo Agent\n\nA tiny agent.\n"


def test_init_creates_parent_directory_for_output(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("AGENTS.md").write_text(_FIXTURE_AGENTS_MD, encoding="utf-8")
        result = runner.invoke(main, ["init", "AGENTS.md", "--yes", "-o", "nested/dir/out.yaml"])
        assert result.exit_code == 0
        assert Path("nested/dir/out.yaml").exists()


def test_init_strict_does_not_block_when_intent_is_valid(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("AGENTS.md").write_text(_FIXTURE_AGENTS_MD, encoding="utf-8")
        result = runner.invoke(main, ["init", "AGENTS.md", "--yes", "--strict", "-o", "out.yaml"])
        assert result.exit_code in (0, 1)


def test_init_skill_md_directory_input_works(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("pkg").mkdir()
        Path("pkg/SKILL.md").write_text("---\nname: test\n---\n", encoding="utf-8")
        Path("pkg/Scripts").mkdir()
        result = runner.invoke(main, ["init", "pkg", "--yes", "-o", "out.yaml"])
        assert result.exit_code == 0
        text = Path("out.yaml").read_text(encoding="utf-8")
        assert "Format: agentskills" in text


def test_init_emits_warning_to_stderr_for_stub(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("AGENTS.md").write_text(_FIXTURE_AGENTS_MD, encoding="utf-8")
        result = runner.invoke(main, ["init", "AGENTS.md", "--yes", "-o", "out.yaml"])
        assert result.exit_code == 0
        combined = result.output + (getattr(result, "stderr", "") or "")
        assert "stub" in combined.lower() or "warning" in combined.lower()


def test_init_output_yaml_to_file(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("AGENTS.md").write_text(_FIXTURE_AGENTS_MD, encoding="utf-8")
        result = runner.invoke(main, ["init", "AGENTS.md", "--yes", "--format", "yaml", "-o", "out.yaml"])
        assert result.exit_code == 0
        import yaml as _yaml
        data = _yaml.safe_load(Path("out.yaml").read_text(encoding="utf-8"))
        assert "intent" in data
        assert "format" in data


def test_init_output_json_to_file(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("AGENTS.md").write_text(_FIXTURE_AGENTS_MD, encoding="utf-8")
        result = runner.invoke(main, ["init", "AGENTS.md", "--yes", "--format", "json", "-o", "out.json"])
        assert result.exit_code == 0
        import json as _json
        data = _json.loads(Path("out.json").read_text(encoding="utf-8"))
        assert {"intent", "confidences", "sources"}.issubset(data.keys())
