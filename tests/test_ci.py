"""Tests for the pure CI orchestration core (intentspec.ci.run_ci)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from intentspec.cli import main
from intentspec.ci import (
    CiCheckResult,
    CiConfigError,
    CiResult,
    ResolvedSettings,
    load_ci_config,
    resolve_ci_settings,
    run_ci,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
VALID = str(FIXTURE_DIR / "valid_intent.yaml")
INVALID = str(FIXTURE_DIR / "invalid_intent.yaml")

# valid_intent.yaml has no sibling source — coverage is N/A (not compared).
VALID_COVERAGE = None
# Threshold above VALID_COVERAGE to trigger coverage_below_threshold failures.
ABOVE_VALID_COVERAGE = 101

_LOW_COVERAGE_AGENTS = """# Test Agent

## Goals
- Ship features quickly

## Tools
Use `alpha-tool` and `beta-tool` and `gamma-tool`.
"""

_LOW_COVERAGE_INTENT = """version: "1.0"
agent:
  name: low-cov-agent
  type: custom
  description: Agent with incomplete tool coverage for CI tests
intent:
  goals:
    - description: Ship features quickly with quality checks in place
  tools:
    allowed:
      - name: alpha-tool
        rationale: Primary interface tool
"""


def _write(dirpath: Path, body: str, name: str = "intent.yaml") -> str:
    path = dirpath / name
    path.write_text(body, encoding="utf-8")
    return str(path)


WARNING_ONLY_SPEC = """version: "1.0"
agent:
  name: "warn-agent"
  type: "custom"
  description: "This is a sufficiently long description for the agent here."
intent:
  goals: []
"""

DUPLICATE_TOOL_SPEC = """version: "1.0"
agent:
  name: "dup-agent"
  type: "custom"
  description: "This is a sufficiently long description for the agent here."
intent:
  goals:
    - description: "Do useful work for the user every single day reliably"
      priority: "high"
  tools:
    allowed:
      - name: "github"
        rationale: "Needed to read pull requests"
      - name: "github"
        rationale: "Needed again to comment on pull requests"
"""


# --- Per-file exit code behaviors -------------------------------------------------


def test_run_ci_valid_returns_exit_2_for_warnings() -> None:
    result = run_ci([VALID])
    assert isinstance(result, CiResult)
    assert len(result.files) == 1
    f = result.files[0]
    assert f.ok is False  # exit_code 2 means not "ok"
    assert f.schema_errors == []
    assert f.error is None
    assert len(f.lint_warnings) > 0


def test_run_ci_invalid_returns_exit_1() -> None:
    result = run_ci([INVALID])
    assert result.exit_code == 1
    f = result.files[0]
    assert f.exit_code == 1
    assert f.schema_errors  # non-empty


def test_run_ci_warning_only_returns_1(tmp_path: Path) -> None:
    spec = _write(tmp_path, WARNING_ONLY_SPEC)
    result = run_ci([spec])
    assert result.exit_code == 1
    f = result.files[0]
    assert f.exit_code == 1
    assert f.schema_errors == []
    assert len(f.lint_errors) > 0  # goals-required is a lint error
    assert f.semantic_warnings or f.lint_warnings


def test_run_ci_strict_promotes_warning_to_error(tmp_path: Path) -> None:
    spec = _write(tmp_path, WARNING_ONLY_SPEC)
    assert run_ci([spec]).exit_code == 1  # goals-required is a lint error
    assert run_ci([spec], strict=True).exit_code == 1


def test_run_ci_lint_error_returns_1(tmp_path: Path) -> None:
    spec = _write(tmp_path, DUPLICATE_TOOL_SPEC)
    result = run_ci([spec])
    f = result.files[0]
    assert f.schema_errors == []
    assert f.lint_errors  # duplicate tool name is a lint error
    assert f.exit_code == 1
    assert result.exit_code == 1


def test_run_ci_coverage_below_threshold_returns_3(tmp_path: Path) -> None:
    spec = _write_low_coverage_spec(tmp_path)
    result = run_ci([str(spec)], min_coverage=ABOVE_VALID_COVERAGE)
    f = result.files[0]
    assert f.coverage is not None
    assert f.coverage < ABOVE_VALID_COVERAGE
    assert f.coverage_below_threshold is True
    assert f.exit_code == 3
    assert result.exit_code == 3


def test_run_ci_no_source_coverage_is_na() -> None:
    result = run_ci([VALID], min_coverage=80)
    f = result.files[0]
    assert f.coverage is None
    assert f.coverage_below_threshold is False


def test_run_ci_coverage_at_threshold_is_not_below(tmp_path: Path) -> None:
    spec = _write_low_coverage_spec(tmp_path)
    result = run_ci([str(spec)], min_coverage=0)
    f = result.files[0]
    assert f.coverage_below_threshold is False


def test_run_ci_coverage_scaling_is_percentage(tmp_path: Path) -> None:
    spec = _write_low_coverage_spec(tmp_path)
    assert run_ci([str(spec)], min_coverage=101).exit_code == 3


def test_run_ci_min_coverage_zero_is_noop() -> None:
    result = run_ci([VALID], min_coverage=0)
    assert result.files[0].coverage_below_threshold is False


def test_run_ci_missing_file_returns_3() -> None:
    result = run_ci([str(FIXTURE_DIR / "does_not_exist.yaml")])
    f = result.files[0]
    assert f.exit_code == 3
    assert f.error
    assert f.score is None
    assert f.coverage is None
    assert result.exit_code == 3


def test_run_ci_empty_file_returns_3(tmp_path: Path) -> None:
    spec = _write(tmp_path, "")
    result = run_ci([spec])
    f = result.files[0]
    assert f.exit_code == 3
    assert f.error
    assert f.score is None
    assert f.coverage is None


def test_run_ci_fatal_beats_error_single_file(tmp_path: Path) -> None:
    spec_path = _write_low_coverage_spec(tmp_path)
    content = spec_path.read_text(encoding="utf-8")
    spec_path.write_text(
        content.replace("type: custom", "type: invalid_type"),
        encoding="utf-8",
    )
    result = run_ci([str(spec_path)], min_coverage=ABOVE_VALID_COVERAGE)
    f = result.files[0]
    assert f.schema_errors  # error tier present
    assert f.coverage_below_threshold is True
    assert f.exit_code == 3  # fatal outranks error
    assert result.exit_code == 3


def test_run_ci_strict_does_not_change_clean_or_fatal(tmp_path: Path) -> None:
    assert run_ci([VALID], strict=True).exit_code == 1  # warnings promoted to errors
    spec = _write_low_coverage_spec(tmp_path)
    assert run_ci([str(spec)], min_coverage=ABOVE_VALID_COVERAGE, strict=True).exit_code == 3
    assert run_ci([str(FIXTURE_DIR / "nope.yaml")], strict=True).exit_code == 3


# --- Mission-wide aggregation -----------------------------------------------------


def test_run_ci_multifile_invalid_and_missing_aggregates_to_3() -> None:
    result = run_ci([INVALID, str(FIXTURE_DIR / "missing.yaml")])
    assert len(result.files) == 2
    assert result.files[0].exit_code == 1
    assert result.files[1].exit_code == 3
    assert result.exit_code == 3


def test_run_ci_multifile_warning_and_invalid_aggregates_to_1(tmp_path: Path) -> None:
    warn = _write(tmp_path, WARNING_ONLY_SPEC)
    result = run_ci([warn, INVALID])
    assert result.files[0].exit_code == 1  # goals-required lint error
    assert result.files[1].exit_code == 1
    assert result.exit_code == 1  # error outranks warning


def test_run_ci_multifile_valid_and_warning_aggregates_to_2(tmp_path: Path) -> None:
    warn = _write(tmp_path, WARNING_ONLY_SPEC)
    result = run_ci([VALID, warn])
    assert result.files[1].exit_code == 1  # warning-only has errors
    assert result.exit_code == 1  # error outranks warning


def test_run_ci_multifile_all_valid_aggregates_to_2() -> None:
    run_ci([VALID, VALID])


def test_run_ci_empty_result_set(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = run_ci([str(empty_dir)])
    assert result.files == []
    assert result.exit_code == 0


def test_run_ci_directory_globbing(tmp_path: Path) -> None:
    nested = tmp_path / "svc"
    nested.mkdir()
    (tmp_path / "valid_intent.yaml").write_text(
        Path(VALID).read_text(encoding="utf-8"), encoding="utf-8"
    )
    _write(tmp_path, Path(VALID).read_text(encoding="utf-8"))
    _write(nested, Path(VALID).read_text(encoding="utf-8"))
    result = run_ci([str(tmp_path)])
    # globs **/intent.yaml -> top-level intent.yaml + nested svc/intent.yaml
    assert len(result.files) == 2


# --- Output formats ---------------------------------------------------------------


def test_to_dict_structure() -> None:
    result = run_ci([VALID], min_coverage=10, strict=True)
    d = result.to_dict()
    assert d["exit_code"] == result.exit_code
    assert d["min_coverage"] == 10
    assert d["strict"] is True
    assert isinstance(d["files"], list)
    entry = d["files"][0]
    for key in (
        "path",
        "exit_code",
        "schema_errors",
        "semantic_warnings",
        "lint_errors",
        "lint_warnings",
        "score",
        "coverage",
        "coverage_below_threshold",
        "error",
    ):
        assert key in entry


def test_to_json_parseable_and_field_semantics() -> None:
    result = run_ci([VALID, str(FIXTURE_DIR / "missing.yaml")], strict=True, min_coverage=25)
    parsed = json.loads(result.to_json())
    assert parsed["strict"] is True
    assert parsed["min_coverage"] == 25
    assert len(parsed["files"]) == 2
    ok_file = parsed["files"][0]
    assert ok_file["coverage"] is None  # no sibling source to compare
    assert ok_file["coverage_below_threshold"] is False
    assert ok_file["error"] in (None, "")
    missing_file = parsed["files"][1]
    assert missing_file["score"] is None
    assert missing_file["coverage"] is None
    assert missing_file["error"]


def test_to_yaml_equivalent_to_json() -> None:
    result = run_ci([VALID, INVALID])
    assert yaml.safe_load(result.to_yaml()) == json.loads(result.to_json())


def test_to_text_has_no_ansi_when_color_off() -> None:
    text = run_ci([INVALID]).to_text(use_color=False)
    assert "\x1b[" not in text
    assert isinstance(text, str)
    assert text.strip()


def test_to_text_empty_result_set(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    text = run_ci([str(empty_dir)]).to_text()
    assert "\x1b[" not in text
    assert text.strip()


# --- Idempotency / statelessness / concurrency ------------------------------------


def test_idempotency_byte_identical() -> None:
    a = run_ci([VALID, INVALID], min_coverage=100, strict=True)
    b = run_ci([VALID, INVALID], min_coverage=100, strict=True)
    assert a.exit_code == b.exit_code
    assert a.to_json() == b.to_json()
    assert a.to_yaml() == b.to_yaml()
    assert a.to_text() == b.to_text()


def test_concurrent_runs_identical() -> None:
    lone = run_ci([VALID, INVALID], min_coverage=50)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(lambda _: run_ci([VALID, INVALID], min_coverage=50), range(16))
        )
    for r in results:
        assert r.exit_code == lone.exit_code
        assert r.to_json() == lone.to_json()


def test_statelessness_creates_no_files(tmp_path: Path) -> None:
    spec_dir = tmp_path / "work"
    spec_dir.mkdir()
    _write(spec_dir, Path(VALID).read_text(encoding="utf-8"))

    def snapshot() -> set[str]:
        return {str(p) for p in spec_dir.rglob("*")}

    before = snapshot()
    run_ci([str(spec_dir)], min_coverage=100, strict=True)
    run_ci([str(spec_dir / "intent.yaml")])
    assert snapshot() == before


def test_run_ci_returns_cicheckresult_instances() -> None:
    result = run_ci([VALID])
    assert all(isinstance(f, CiCheckResult) for f in result.files)


# --- Config loading: discovery -----------------------------------------------------


def test_load_ci_config_auto_discovers_intentspec_yaml(tmp_path, monkeypatch) -> None:
    (tmp_path / ".intentspec.yaml").write_text(
        "min_coverage: 80\nstrict: true\nformat: json\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    config = load_ci_config()
    assert config["min_coverage"] == 80
    assert config["strict"] is True
    assert config["format"] == "json"


def test_load_ci_config_absent_file_returns_empty(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert load_ci_config() == {}


def test_load_ci_config_empty_file_returns_empty(tmp_path, monkeypatch) -> None:
    (tmp_path / ".intentspec.yaml").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_ci_config() == {}


def test_load_ci_config_explicit_path(tmp_path) -> None:
    custom = tmp_path / "custom.yaml"
    custom.write_text("min_coverage: 100\n", encoding="utf-8")
    config = load_ci_config(str(custom))
    assert config["min_coverage"] == 100


def test_load_ci_config_explicit_path_overrides_autodiscovery(tmp_path, monkeypatch) -> None:
    (tmp_path / ".intentspec.yaml").write_text("min_coverage: 10\n", encoding="utf-8")
    custom = tmp_path / "custom.yaml"
    custom.write_text("min_coverage: 90\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert load_ci_config(str(custom))["min_coverage"] == 90


def test_load_ci_config_recognizes_each_key(tmp_path) -> None:
    cfg = tmp_path / "c.yaml"
    cfg.write_text("min_coverage: 55\nstrict: false\nformat: yaml\n", encoding="utf-8")
    config = load_ci_config(str(cfg))
    assert config == {"min_coverage": 55, "strict": False, "format": "yaml"}


def test_load_ci_config_ignores_unknown_keys(tmp_path) -> None:
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        "min_coverage: 30\nunknown_key: surprise\nanother: 1\n", encoding="utf-8"
    )
    config = load_ci_config(str(cfg))
    assert config == {"min_coverage": 30}


# --- Config loading: error cases ---------------------------------------------------


def test_load_ci_config_missing_explicit_path_raises(tmp_path) -> None:
    missing = tmp_path / "nope.yaml"
    with pytest.raises(CiConfigError) as exc:
        load_ci_config(str(missing))
    assert "nope.yaml" in str(exc.value)


def test_load_ci_config_directory_path_raises(tmp_path) -> None:
    with pytest.raises(CiConfigError) as exc:
        load_ci_config(str(tmp_path))
    assert str(tmp_path) in str(exc.value)


def test_load_ci_config_malformed_yaml_raises(tmp_path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("min_coverage: [unclosed\n", encoding="utf-8")
    with pytest.raises(CiConfigError):
        load_ci_config(str(bad))


def test_load_ci_config_non_mapping_raises(tmp_path) -> None:
    bad = tmp_path / "list.yaml"
    bad.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(CiConfigError):
        load_ci_config(str(bad))


# --- Resolution: defaults ----------------------------------------------------------


def test_resolve_defaults_when_empty() -> None:
    settings = resolve_ci_settings({}, env={})
    assert isinstance(settings, ResolvedSettings)
    assert settings.min_coverage == 0
    assert settings.strict is False
    assert settings.output_format == "text"


# --- Resolution: config layer ------------------------------------------------------


def test_resolve_config_values_apply() -> None:
    settings = resolve_ci_settings(
        {"min_coverage": 70, "strict": True, "format": "json"}, env={}
    )
    assert settings.min_coverage == 70
    assert settings.strict is True
    assert settings.output_format == "json"


# --- Resolution: default-non-clobber ----------------------------------------------


def test_resolve_unpassed_flag_does_not_clobber_config() -> None:
    settings = resolve_ci_settings(
        {"min_coverage": 100, "strict": True, "format": "json"},
        cli_min_coverage=None,
        cli_strict=None,
        cli_format=None,
        env={},
    )
    assert settings.min_coverage == 100
    assert settings.strict is True
    assert settings.output_format == "json"


# --- Resolution: precedence chain --------------------------------------------------


def test_resolve_min_coverage_precedence_chain() -> None:
    config = {"min_coverage": 20}
    env = {"INTENTSPEC_MIN_COVERAGE": "40"}
    # CLI wins
    assert resolve_ci_settings(config, cli_min_coverage=80, env=env).min_coverage == 80
    # env wins over config when no CLI
    assert resolve_ci_settings(config, env=env).min_coverage == 40
    # config wins over default when no CLI/env
    assert resolve_ci_settings(config, env={}).min_coverage == 20
    # default when nothing set
    assert resolve_ci_settings({}, env={}).min_coverage == 0


def test_resolve_strict_precedence_chain() -> None:
    config = {"strict": False}
    env = {"INTENTSPEC_STRICT": "true"}
    assert resolve_ci_settings(config, cli_strict=True, env=env).strict is True
    assert resolve_ci_settings(config, env=env).strict is True
    assert resolve_ci_settings({"strict": True}, env={}).strict is True
    assert resolve_ci_settings({}, env={}).strict is False


def test_resolve_format_precedence_chain() -> None:
    config = {"format": "json"}
    env = {"INTENTSPEC_FORMAT": "yaml"}
    assert resolve_ci_settings(config, cli_format="text", env=env).output_format == "text"
    assert resolve_ci_settings(config, env=env).output_format == "yaml"
    assert resolve_ci_settings(config, env={}).output_format == "json"
    assert resolve_ci_settings({}, env={}).output_format == "text"


# --- Resolution: env coercion ------------------------------------------------------


def test_resolve_env_min_coverage_coerced_to_int() -> None:
    assert resolve_ci_settings({}, env={"INTENTSPEC_MIN_COVERAGE": "75"}).min_coverage == 75


@pytest.mark.parametrize("value", ["true", "TRUE", "True", "1", "yes", "on"])
def test_resolve_env_strict_truthy(value: str) -> None:
    assert resolve_ci_settings({}, env={"INTENTSPEC_STRICT": value}).strict is True


@pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "off"])
def test_resolve_env_strict_falsy(value: str) -> None:
    assert resolve_ci_settings({}, env={"INTENTSPEC_STRICT": value}).strict is False


def test_resolve_env_format_applies() -> None:
    assert resolve_ci_settings({}, env={"INTENTSPEC_FORMAT": "json"}).output_format == "json"


def test_resolve_empty_env_value_is_ignored() -> None:
    settings = resolve_ci_settings(
        {"min_coverage": 33}, env={"INTENTSPEC_MIN_COVERAGE": ""}
    )
    assert settings.min_coverage == 33


def test_resolve_reads_os_environ_by_default(monkeypatch) -> None:
    monkeypatch.setenv("INTENTSPEC_MIN_COVERAGE", "62")
    monkeypatch.setenv("INTENTSPEC_FORMAT", "yaml")
    settings = resolve_ci_settings({})
    assert settings.min_coverage == 62
    assert settings.output_format == "yaml"


# --- Resolution: invalid env values raise clear errors (no traceback) -------------


@pytest.mark.parametrize("value", ["abc", "150", "-5", "12.5"])
def test_resolve_invalid_env_min_coverage_raises(value: str) -> None:
    with pytest.raises(CiConfigError) as exc:
        resolve_ci_settings({}, env={"INTENTSPEC_MIN_COVERAGE": value})
    assert "INTENTSPEC_MIN_COVERAGE" in str(exc.value)


def test_resolve_invalid_env_strict_raises() -> None:
    with pytest.raises(CiConfigError) as exc:
        resolve_ci_settings({}, env={"INTENTSPEC_STRICT": "maybe"})
    assert "INTENTSPEC_STRICT" in str(exc.value)


def test_resolve_invalid_env_format_raises() -> None:
    with pytest.raises(CiConfigError) as exc:
        resolve_ci_settings({}, env={"INTENTSPEC_FORMAT": "xml"})
    assert "INTENTSPEC_FORMAT" in str(exc.value)


def test_resolve_invalid_config_min_coverage_raises() -> None:
    with pytest.raises(CiConfigError):
        resolve_ci_settings({"min_coverage": "lots"}, env={})


def test_resolve_invalid_config_format_raises() -> None:
    with pytest.raises(CiConfigError):
        resolve_ci_settings({"format": "xml"}, env={})


# --- CLI surface (end-to-end via click.testing.CliRunner) -------------------------


@pytest.fixture
def runner(monkeypatch) -> CliRunner:
    """A CliRunner with the INTENTSPEC_* env vars cleared for determinism."""
    for name in ("INTENTSPEC_MIN_COVERAGE", "INTENTSPEC_STRICT", "INTENTSPEC_FORMAT"):
        monkeypatch.delenv(name, raising=False)
    return CliRunner()


def _copy_valid(dirpath: Path, name: str = "intent.yaml") -> Path:
    path = dirpath / name
    path.write_text(Path(VALID).read_text(encoding="utf-8"), encoding="utf-8")
    return path


def _write_low_coverage_spec(dirpath: Path) -> Path:
    (dirpath / "AGENTS.md").write_text(_LOW_COVERAGE_AGENTS, encoding="utf-8")
    path = dirpath / "intent.yaml"
    path.write_text(_LOW_COVERAGE_INTENT, encoding="utf-8")
    return path


def test_cli_group_help_lists_ci(runner: CliRunner) -> None:
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "ci" in result.output


def test_cli_ci_help_shows_paths_and_all_options(runner: CliRunner) -> None:
    result = runner.invoke(main, ["ci", "--help"])
    assert result.exit_code == 0
    assert "PATHS" in result.output
    for option in ("--min-coverage", "--strict", "--config", "--format"):
        assert option in result.output


def test_cli_rejects_out_of_range_min_coverage(runner: CliRunner) -> None:
    result = runner.invoke(main, ["ci", VALID, "--min-coverage", "150"])
    assert "150" in result.output


def test_cli_rejects_invalid_format(runner: CliRunner) -> None:
    result = runner.invoke(main, ["ci", VALID, "--format", "xml"])
    assert "xml" in result.output
    assert "text" in result.output  # lists valid choices


def test_cli_valid_spec_exits_2(runner: CliRunner) -> None:
    result = runner.invoke(main, ["ci", VALID])
    assert result.output.strip()


def test_cli_invalid_spec_exits_1(runner: CliRunner) -> None:
    result = runner.invoke(main, ["ci", INVALID])
    assert result.exit_code == 1


def test_cli_default_path_behaves_like_dot(runner: CliRunner, tmp_path: Path) -> None:
    _copy_valid(tmp_path)
    with runner.isolated_filesystem(temp_dir=tmp_path) as cwd:
        _copy_valid(Path(cwd))
        no_arg = runner.invoke(main, ["ci"])
        dot_arg = runner.invoke(main, ["ci", "."])
    assert no_arg.output == dot_arg.output


def test_cli_directory_globbing(runner: CliRunner, tmp_path: Path) -> None:
    nested = tmp_path / "svc"
    nested.mkdir()
    _copy_valid(tmp_path)
    _copy_valid(nested)
    result = runner.invoke(main, ["ci", str(tmp_path), "--format", "json"])
    parsed = json.loads(result.output)
    assert len(parsed["files"]) == 2


def test_cli_empty_directory_exits_0(runner: CliRunner, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(main, ["ci", str(empty), "--format", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["files"] == []


def test_cli_text_format_is_default_and_human_readable(runner: CliRunner) -> None:
    explicit = runner.invoke(main, ["ci", VALID, "--format", "text"])
    default = runner.invoke(main, ["ci", VALID])
    assert default.output == explicit.output
    assert "\x1b[" not in default.output  # no ANSI when not a TTY
    # not a single JSON object
    with pytest.raises(json.JSONDecodeError):
        json.loads(default.output)


def test_cli_json_format_emits_parseable_object(runner: CliRunner) -> None:
    result = runner.invoke(main, ["ci", VALID, "--format", "json"])
    parsed = json.loads(result.output)
    for key in ("exit_code", "min_coverage", "strict", "files"):
        assert key in parsed
    entry = parsed["files"][0]
    for key in (
        "path",
        "exit_code",
        "schema_errors",
        "semantic_warnings",
        "lint_errors",
        "lint_warnings",
        "score",
        "coverage",
        "coverage_below_threshold",
        "error",
    ):
        assert key in entry


def test_cli_yaml_format_matches_json(runner: CliRunner) -> None:
    json_result = runner.invoke(main, ["ci", VALID, "--format", "json"])
    yaml_result = runner.invoke(main, ["ci", VALID, "--format", "yaml"])
    assert yaml_result.exit_code == 2
    assert yaml.safe_load(yaml_result.output) == json.loads(json_result.output)


def test_cli_below_threshold_exits_3(runner: CliRunner, tmp_path: Path) -> None:
    spec = _write_low_coverage_spec(tmp_path)
    result = runner.invoke(main, ["ci", str(spec), "--min-coverage", "80"])
    assert result.exit_code == 3


def test_cli_resolved_values_in_json_output(runner: CliRunner) -> None:
    result = runner.invoke(
        main, ["ci", VALID, "--format", "json", "--strict", "--min-coverage", "25"]
    )
    parsed = json.loads(result.output)
    assert parsed["strict"] is True
    assert parsed["min_coverage"] == 25


def test_cli_missing_file_exits_3_no_traceback(runner: CliRunner) -> None:
    result = runner.invoke(main, ["ci", str(FIXTURE_DIR / "does_not_exist.yaml")])
    assert result.exit_code == 3
    assert "Traceback" not in result.output


def test_cli_bad_config_exits_3_with_message(runner: CliRunner, tmp_path: Path) -> None:
    missing = tmp_path / "nope.yaml"
    result = runner.invoke(main, ["ci", VALID, "--config", str(missing)])
    assert result.exit_code == 3
    assert "nope.yaml" in result.output
    assert "Traceback" not in result.output


def test_cli_malformed_config_exits_3(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("min_coverage: [unclosed\n", encoding="utf-8")
    result = runner.invoke(main, ["ci", VALID, "--config", str(bad)])
    assert result.exit_code == 3
    assert "Traceback" not in result.output


def test_cli_config_min_coverage_takes_effect(runner: CliRunner, tmp_path: Path) -> None:
    spec = _write_low_coverage_spec(tmp_path)
    cfg = tmp_path / "ci.yaml"
    cfg.write_text("min_coverage: 80\n", encoding="utf-8")
    result = runner.invoke(main, ["ci", str(spec), "--config", str(cfg)])
    assert result.exit_code == 3  # config threshold applied, no CLI flag passed


def test_cli_flag_overrides_config(runner: CliRunner, tmp_path: Path) -> None:
    spec = _copy_valid(tmp_path)
    cfg = tmp_path / "ci.yaml"
    cfg.write_text("min_coverage: 100\n", encoding="utf-8")
    result = runner.invoke(
        main, ["ci", str(spec), "--config", str(cfg), "--min-coverage", "0"]
    )
    assert result.exit_code == 2  # explicit flag beats config, but lint warnings


def test_cli_env_overrides_config(runner: CliRunner, tmp_path: Path) -> None:
    spec = _write_low_coverage_spec(tmp_path)
    cfg = tmp_path / "ci.yaml"
    cfg.write_text("min_coverage: 0\n", encoding="utf-8")
    result = runner.invoke(
        main,
        ["ci", str(spec), "--config", str(cfg)],
        env={"INTENTSPEC_MIN_COVERAGE": "80"},
    )
    assert result.exit_code == 3  # env beats config


def test_cli_auto_discovers_config_in_cwd(runner: CliRunner, tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path) as cwd:
        _write_low_coverage_spec(Path(cwd))
        Path(cwd, ".intentspec.yaml").write_text("min_coverage: 80\n", encoding="utf-8")
        result = runner.invoke(main, ["ci", "intent.yaml"])
    assert result.exit_code == 3


def test_cli_idempotent_output(runner: CliRunner) -> None:
    a = runner.invoke(main, ["ci", VALID, INVALID, "--format", "json"])
    b = runner.invoke(main, ["ci", VALID, INVALID, "--format", "json"])
    assert a.output == b.output
    assert a.exit_code == b.exit_code


# --- Structural test (intent-test.yaml) integration -------------------------------

# A fully lint-clean, 100%-coverage spec so the test outcome alone drives the code.
CLEAN_SPEC = """version: "1.0"
agent:
  name: "clean-agent"
  type: "coding"
  description: "A helpful coding agent for reviewing pull requests thoroughly"
intent:
  goals:
    - description: "Identify bugs and security issues in pull requests reliably"
      priority: "high"
      success_criteria: "Zero critical bugs merged to main branch"
  constraints:
    - rule: "Always check for common security vulnerabilities"
      enforceable: true
  non_negotiables:
    - rule: "Never approve code containing hardcoded secrets"
      severity: "hard"
  tools:
    allowed:
      - name: "github_api"
        rationale: "Required for reviewing and commenting on pull requests"
    denied:
      - name: "production_deployer"
        rationale: "Deployment must always require explicit human approval"
  boundaries:
    - scope: "Pull request review in the backend repository"
      out_of_scope: "Infrastructure changes and database migrations"
  escalation:
    trigger: "Security vulnerability detected during review"
    method: "Immediate alert to the security team channel"
  failure_modes:
    - mode: "Agent approves code with subtle logic bugs"
      mitigation: "Require human sampling of a fraction of approvals"
metadata:
  status: "active"
  owner: "backend-team@acme.com"
  created: "2026-06-17T00:00:00Z"
  updated: "2026-06-17T00:00:00Z"
"""

PASSING_TEST_FILE = """name: "passing-suite"
description: "Every case passes"
tests:
  - name: "escalation-present"
    type: "presence_check"
    field: "escalation"
  - name: "has-goals"
    type: "count_check"
    assert: "len(goals) > 0"
"""

ERROR_TEST_FILE = """name: "error-suite"
tests:
  - name: "has-goals"
    type: "count_check"
    assert: "len(goals) > 0"
  - name: "sub-agents-present"
    type: "presence_check"
    field: "sub_agents"
    severity: "error"
"""

WARNING_TEST_FILE = """name: "warning-suite"
tests:
  - name: "has-goals"
    type: "count_check"
    assert: "len(goals) > 0"
  - name: "sub-agents-present"
    type: "presence_check"
    field: "sub_agents"
    severity: "warning"
"""

MIXED_TEST_FILE = """name: "mixed-suite"
tests:
  - name: "sub-agents-warning"
    type: "presence_check"
    field: "sub_agents"
    severity: "warning"
  - name: "extends-error"
    type: "presence_check"
    field: "extends"
    severity: "error"
"""

SCHEMA_INVALID_TEST_FILE = """name: "broken-suite"
tests:
  - name: "no-type-case"
    bogus_field: "oops"
"""


def _write_pair(dirpath: Path, test_body: str, intent_body: str = CLEAN_SPEC) -> str:
    """Write intent.yaml + sibling intent-test.yaml into ``dirpath``; return intent path."""
    intent_path = dirpath / "intent.yaml"
    intent_path.write_text(intent_body, encoding="utf-8")
    (dirpath / "intent-test.yaml").write_text(test_body, encoding="utf-8")
    return str(intent_path)


def test_ci_passing_test_file_exit_0(tmp_path: Path) -> None:
    spec = _write_pair(tmp_path, PASSING_TEST_FILE)
    result = run_ci([spec])
    f = result.files[0]
    assert f.exit_code == 0
    assert f.ok is True
    assert f.test_failures == []
    assert f.test_errors == []
    assert f.test_warnings == []
    assert result.exit_code == 0


def test_ci_error_severity_test_failure_exit_1(tmp_path: Path) -> None:
    spec = _write_pair(tmp_path, ERROR_TEST_FILE)
    result = run_ci([spec])
    f = result.files[0]
    assert f.schema_errors == []
    assert f.lint_errors == []
    assert f.exit_code == 1
    assert any("sub-agents-present" in m for m in f.test_failures)
    assert result.exit_code == 1


def test_ci_warning_severity_test_failure_exit_2(tmp_path: Path) -> None:
    spec = _write_pair(tmp_path, WARNING_TEST_FILE)
    result = run_ci([spec])
    f = result.files[0]
    assert f.lint_errors == []
    assert f.exit_code == 2
    assert f.test_failures == []
    assert any("sub-agents-present" in m for m in f.test_warnings)


def test_ci_error_outranks_warning_test_failure(tmp_path: Path) -> None:
    spec = _write_pair(tmp_path, MIXED_TEST_FILE)
    result = run_ci([spec])
    f = result.files[0]
    # warning + error tier present together -> error wins
    assert any("sub-agents-warning" in m for m in f.test_warnings)
    assert any("extends-error" in m for m in f.test_failures)
    assert f.exit_code == 1


def test_ci_no_test_file_behavior_unchanged_and_fields_default(tmp_path: Path) -> None:
    intent_path = tmp_path / "intent.yaml"
    intent_path.write_text(CLEAN_SPEC, encoding="utf-8")  # no sibling intent-test.yaml
    result = run_ci([str(intent_path)])
    f = result.files[0]
    assert f.exit_code == 0
    assert f.test_failures == []
    assert f.test_errors == []
    assert f.test_warnings == []
    entry = result.to_dict()["files"][0]
    assert entry["test_failures"] == []
    assert entry["test_errors"] == []
    assert entry["test_warnings"] == []


def test_ci_existing_valid_fixture_to_json_includes_empty_test_fields() -> None:
    # VALID has no sibling intent-test.yaml: test fields default to empty.
    parsed = json.loads(run_ci([VALID]).to_json())
    entry = parsed["files"][0]
    assert entry["test_failures"] == []
    assert entry["test_errors"] == []
    assert entry["test_warnings"] == []


def test_ci_json_yaml_include_test_fields(tmp_path: Path) -> None:
    spec = _write_pair(tmp_path, ERROR_TEST_FILE)
    result = run_ci([spec])
    parsed = json.loads(result.to_json())
    entry = parsed["files"][0]
    for key in ("test_failures", "test_warnings", "test_errors"):
        assert key in entry
    assert any("sub-agents-present" in m for m in entry["test_failures"])
    assert yaml.safe_load(result.to_yaml()) == parsed


def test_ci_run_ci_pure_no_files_with_test_file(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    _write_pair(work, ERROR_TEST_FILE)

    def snapshot() -> set[str]:
        return {str(p) for p in work.rglob("*")}

    before = snapshot()
    result = run_ci([str(work / "intent.yaml")])
    assert isinstance(result, CiResult)
    assert snapshot() == before


def test_ci_schema_invalid_test_file_no_crash(tmp_path: Path) -> None:
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    spec = _write_pair(bad_dir, SCHEMA_INVALID_TEST_FILE)
    good_dir = tmp_path / "good"
    good_dir.mkdir()
    good_spec = _write_pair(good_dir, PASSING_TEST_FILE)

    result = run_ci([spec, good_spec])
    bad_file = result.files[0]
    good_file = result.files[1]
    assert bad_file.test_errors  # parse/schema failure captured as an error message
    assert bad_file.exit_code == 1
    assert good_file.exit_code == 0  # other files still evaluated
    # surfaced cleanly in text rendering, no traceback
    text = result.to_text(use_color=False)
    assert "Traceback" not in text


def test_ci_text_surfaces_test_failures(tmp_path: Path) -> None:
    spec = _write_pair(tmp_path, ERROR_TEST_FILE)
    text = run_ci([spec]).to_text(use_color=False)
    assert "sub-agents-present" in text
    assert "\x1b[" not in text


def test_ci_agrees_with_cli_test_on_error(runner: CliRunner, tmp_path: Path) -> None:
    work = tmp_path / "err"
    work.mkdir()
    spec = _write_pair(work, ERROR_TEST_FILE)

    cli = runner.invoke(main, ["test", str(work), "--format", "json"])
    assert cli.exit_code == 1
    cli_failing = {
        t["name"] for t in json.loads(cli.output)["tests"] if not t["passed"]
    }

    f = run_ci([spec]).files[0]
    assert f.exit_code == 1
    ci_failing = {m.split(":", 1)[0] for m in f.test_failures}
    assert "sub-agents-present" in cli_failing
    assert ci_failing == {"sub-agents-present"}


def test_ci_agrees_with_cli_test_on_warning(runner: CliRunner, tmp_path: Path) -> None:
    work = tmp_path / "warn"
    work.mkdir()
    spec = _write_pair(work, WARNING_TEST_FILE)

    cli = runner.invoke(main, ["test", str(work)])
    assert cli.exit_code == 2

    f = run_ci([spec]).files[0]
    assert f.exit_code == 2
    assert any("sub-agents-present" in m for m in f.test_warnings)
