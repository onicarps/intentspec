"""Tests for the pure CI orchestration core (intentspec.ci.run_ci)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from intentspec.ci import CiCheckResult, CiResult, run_ci

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
