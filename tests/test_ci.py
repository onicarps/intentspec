"""Tests for the pure CI orchestration core (intentspec.ci.run_ci)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import yaml

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

# Computed coverage percentage for valid_intent.yaml (round(overall * 100)).
VALID_COVERAGE = 45


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


def test_run_ci_valid_returns_exit_0() -> None:
    result = run_ci([VALID])
    assert isinstance(result, CiResult)
    assert result.exit_code == 0
    assert len(result.files) == 1
    f = result.files[0]
    assert f.exit_code == 0
    assert f.ok is True
    assert f.schema_errors == []
    assert f.error is None


def test_run_ci_invalid_returns_exit_1() -> None:
    result = run_ci([INVALID])
    assert result.exit_code == 1
    f = result.files[0]
    assert f.exit_code == 1
    assert f.schema_errors  # non-empty


def test_run_ci_warning_only_returns_2(tmp_path: Path) -> None:
    spec = _write(tmp_path, WARNING_ONLY_SPEC)
    result = run_ci([spec])
    assert result.exit_code == 2
    f = result.files[0]
    assert f.exit_code == 2
    assert f.schema_errors == []
    assert f.lint_errors == []
    assert f.semantic_warnings or f.lint_warnings


def test_run_ci_strict_promotes_warning_to_error(tmp_path: Path) -> None:
    spec = _write(tmp_path, WARNING_ONLY_SPEC)
    assert run_ci([spec]).exit_code == 2
    assert run_ci([spec], strict=True).exit_code == 1


def test_run_ci_lint_error_returns_1(tmp_path: Path) -> None:
    spec = _write(tmp_path, DUPLICATE_TOOL_SPEC)
    result = run_ci([spec])
    f = result.files[0]
    assert f.schema_errors == []
    assert f.lint_errors  # duplicate tool name is a lint error
    assert f.exit_code == 1
    assert result.exit_code == 1


def test_run_ci_coverage_below_threshold_returns_3() -> None:
    result = run_ci([VALID], min_coverage=100)
    f = result.files[0]
    assert f.coverage == VALID_COVERAGE
    assert f.coverage_below_threshold is True
    assert f.exit_code == 3
    assert result.exit_code == 3


def test_run_ci_coverage_at_threshold_is_not_below() -> None:
    result = run_ci([VALID], min_coverage=VALID_COVERAGE)
    f = result.files[0]
    assert f.coverage_below_threshold is False
    assert f.exit_code == 0


def test_run_ci_coverage_scaling_is_percentage() -> None:
    assert run_ci([VALID], min_coverage=VALID_COVERAGE - 15).exit_code == 0
    assert run_ci([VALID], min_coverage=VALID_COVERAGE + 15).exit_code == 3


def test_run_ci_min_coverage_zero_is_noop() -> None:
    result = run_ci([VALID], min_coverage=0)
    assert result.files[0].coverage_below_threshold is False
    assert result.exit_code == 0


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


def test_run_ci_fatal_beats_error_single_file() -> None:
    result = run_ci([INVALID], min_coverage=100)
    f = result.files[0]
    assert f.schema_errors  # error tier present
    assert f.coverage_below_threshold is True
    assert f.exit_code == 3  # fatal outranks error
    assert result.exit_code == 3


def test_run_ci_strict_does_not_change_clean_or_fatal() -> None:
    assert run_ci([VALID], strict=True).exit_code == 0
    assert run_ci([VALID], min_coverage=100, strict=True).exit_code == 3
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
    assert result.files[0].exit_code == 2
    assert result.files[1].exit_code == 1
    assert result.exit_code == 1  # error outranks warning


def test_run_ci_multifile_valid_and_warning_aggregates_to_2(tmp_path: Path) -> None:
    warn = _write(tmp_path, WARNING_ONLY_SPEC)
    result = run_ci([VALID, warn])
    assert result.files[0].exit_code == 0
    assert result.files[1].exit_code == 2
    assert result.exit_code == 2


def test_run_ci_multifile_all_valid_aggregates_to_0() -> None:
    result = run_ci([VALID, VALID])
    assert result.exit_code == 0


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
    assert all(f.exit_code == 0 for f in result.files)


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
    assert isinstance(ok_file["coverage"], int)
    assert 0 <= ok_file["coverage"] <= 100
    assert isinstance(ok_file["coverage_below_threshold"], bool)
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
