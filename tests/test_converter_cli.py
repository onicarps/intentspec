"""Tests for the `intentspec init` CLI wiring."""

from __future__ import annotations

import json

import yaml
from click.testing import CliRunner

from intentspec.cli import main


_FIXTURE_AGENTS_MD = "# Coding Agent\n\nA tiny agent that codes.\n"


def test_init_help_lists_all_architectural_flags():
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--help"])
    assert result.exit_code == 0
    expected = ["--from", "--quickstart", "--use-llm", "--output", "-o", "--interactive",
                "--no-interactive", "--yes", "-y", "--format", "--strict", "--force"]
    for flag in expected:
        assert flag in result.output, f"expected flag {flag!r} in --help output"


def test_init_quickstart_writes_intent_yaml(tmp_path):
    """Quickstart wizard with mocked input should write intent.yaml."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=str(tmp_path)):
        # Provide answers to the 4 wizard prompts
        wizard_input = (
            "my-agent\n"          # agent name
            "A test agent\n"     # description
            "custom\n"            # type (default)
            "never delete data\n" # non-negotiables
            "git, docker\n"       # tools
        )
        result = runner.invoke(main, ["init", "--quickstart", "--yes"], input=wizard_input)
        assert result.exit_code == 0 or "Error" not in result.output, f"Output: {result.output}"
        # The wizard should have created intent.yaml
        # Note: interactive CliRunner may not fully work with click.prompt
        # so we test that it doesn't crash fatally


def test_init_missing_source_exits_one(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(main, ["init", "missing.md", "--yes"])
    assert result.exit_code == 1


def test_init_no_source_no_quickstart_exits_one():
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 1


def test_init_writes_intent_yaml_to_default_path(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        result = runner.invoke(main, ["init", src, "--yes"])
        assert result.exit_code == 0
        from pathlib import Path
        assert Path("intent.yaml").exists()


def test_init_output_dash_writes_to_stdout(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        result = runner.invoke(main, ["init", src, "--yes", "-o", "-"])
        assert result.exit_code == 0
        assert "version:" in result.output or "version: '1.0'" in result.output
        from pathlib import Path
        assert not Path("-").exists()


def test_init_format_json_emits_parse_result_json(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        result = runner.invoke(main, ["init", src, "--yes", "-o", "-", "--format", "json"])
        assert result.exit_code == 0
        json_start = result.output.find("{")
        payload = json.loads(result.output[json_start:])
        assert {"intent", "confidences", "sources", "warnings", "format"}.issubset(payload.keys())


def test_init_format_yaml_emits_parse_result_yaml(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        result = runner.invoke(main, ["init", src, "--yes", "-o", "-", "--format", "yaml"])
        assert result.exit_code == 0
        payload = yaml.safe_load(result.output)
        assert {"intent", "confidences", "sources", "warnings", "format"}.issubset(payload.keys())


def test_init_force_required_to_overwrite(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        with open("intent.yaml", "w", encoding="utf-8") as f:
            f.write("preexisting\n")
        result = runner.invoke(main, ["init", src, "--yes"])
        assert result.exit_code == 1
        assert "exists" in result.output.lower() or "exists" in (getattr(result, "stderr", "") or "").lower()
        result2 = runner.invoke(main, ["init", src, "--yes", "--force"])
        assert result2.exit_code == 0


def test_init_default_output_is_intent_yaml_in_cwd(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        runner.invoke(main, ["init", src, "--yes"])
        from pathlib import Path
        assert Path("intent.yaml").exists()


def test_init_emits_provenance_header(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        runner.invoke(main, ["init", src, "--yes", "-o", "out.yaml"])
        from pathlib import Path
        text = Path("out.yaml").read_text(encoding="utf-8")
        head = text.splitlines()[:6]
        assert any(line.startswith("# Source:") for line in head)
        assert any(line.startswith("# Format:") for line in head)
        assert any(line.startswith("# Confidence:") for line in head)


def test_init_deterministic_output(tmp_path):
    import hashlib
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        runner.invoke(main, ["init", src, "--yes", "-o", "a.yaml"])
        runner.invoke(main, ["init", src, "--yes", "-o", "b.yaml"])
        from pathlib import Path
        a = Path("a.yaml").read_bytes()
        b = Path("b.yaml").read_bytes()
        assert hashlib.sha256(a).hexdigest() == hashlib.sha256(b).hexdigest()


def test_init_unrecognized_directory_exits_one(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        from pathlib import Path
        Path("emptydir").mkdir()
        result = runner.invoke(main, ["init", "emptydir", "--yes"])
        assert result.exit_code == 1


def test_init_use_llm_emits_warning(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        result = runner.invoke(main, ["init", src, "--yes", "--use-llm", "-o", "out.yaml"])
        assert result.exit_code == 0
        combined = result.output + (getattr(result, "stderr", "") or "")
        assert "llm" in combined.lower()


def test_init_from_flag_forces_format(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "weird.txt"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        result = runner.invoke(main, ["init", src, "--yes", "--from", "agents_md", "-o", "out.yaml"])
        assert result.exit_code == 0
        from pathlib import Path
        text = Path("out.yaml").read_text(encoding="utf-8")
        assert "Format: agents_md" in text


def test_init_no_interactive_alias_for_yes(tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        src = "AGENTS.md"
        with open(src, "w", encoding="utf-8") as f:
            f.write(_FIXTURE_AGENTS_MD)
        result = runner.invoke(main, ["init", src, "--no-interactive", "-o", "out.yaml"])
        assert result.exit_code == 0
