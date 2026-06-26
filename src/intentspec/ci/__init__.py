"""CI orchestration core for IntentSpec.

This module aggregates the existing ``validate``, ``lint``, ``score``, and
``coverage`` capabilities into a single unified result with one exit code. It
reuses those modules and never reimplements their logic.

``run_ci`` is pure: it computes and returns a :class:`CiResult`. It never calls
``sys.exit``, never prints, writes no files, and mutates no global state.
Rendering and process exit belong to the CLI layer.
"""

from __future__ import annotations

import glob
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import yaml

from intentspec.ci.config import (
    CiConfigError,
    ResolvedSettings,
    load_ci_config,
    resolve_ci_settings,
)
from intentspec.coverage import analyze_coverage
from intentspec.source_resolve import read_source_text, resolve_source_for_intent
from intentspec.lint import lint_intent
from intentspec.models.intent import IntentValidationError
from intentspec.score.ids import compute_ids
from intentspec.spec.formatter import Formatter
from intentspec.spec.validate import validate_file
from intentspec.test_engine import run_intent_tests
from intentspec.test_schema import IntentTestSchemaError, parse_intent_test

__all__ = [
    "CiCheckResult",
    "CiConfigError",
    "CiResult",
    "ResolvedSettings",
    "load_ci_config",
    "resolve_ci_settings",
    "run_ci",
]

# Aggregation rank: pass(0) < warning(2) < error(1) < fatal(3). Numeric codes
# are intentionally non-monotonic with rank.
_RANK: dict[int, int] = {0: 0, 2: 1, 1: 2, 3: 3}

_VERDICT: dict[int, str] = {0: "PASS", 1: "ERROR", 2: "WARNING", 3: "FATAL"}


@dataclass
class CiCheckResult:
    """Per-file aggregated result of the four checks.

    Attributes:
        path: Display path of the checked file.
        ok: True when this file's individual exit code is 0.
        exit_code: This file's individual code (0/1/2/3).
        schema_errors: Schema validation error messages.
        semantic_warnings: Semantic validation warning messages.
        lint_errors: Lint error messages.
        lint_warnings: Lint warning messages.
        score: Intent Debt Score (0-100), or None if unprocessable.
        coverage: Coverage percentage 0-100, or None if unprocessable.
        coverage_below_threshold: True when coverage is below ``min_coverage``.
        error: Set when the file could not be processed (missing/empty/unreadable).
        test_failures: Error-severity structural-test failure messages (sibling
            ``intent-test.yaml``); empty when there is no test file.
        test_warnings: Warning-severity structural-test failure messages; empty
            when there is no test file.
        test_errors: Structural-test evaluation/schema error messages (e.g. a
            schema-invalid test file or unparseable assertion); empty when there is
            no test file.
    """

    path: str
    ok: bool
    exit_code: int
    schema_errors: list[str]
    semantic_warnings: list[str]
    lint_errors: list[str]
    lint_warnings: list[str]
    score: float | None
    coverage: int | None
    coverage_below_threshold: bool
    error: str | None
    test_failures: list[str] = field(default_factory=list)
    test_warnings: list[str] = field(default_factory=list)
    test_errors: list[str] = field(default_factory=list)


@dataclass
class CiResult:
    """Mission-wide aggregated result across all resolved paths.

    Attributes:
        files: Per-file results in stable order.
        exit_code: Final aggregated code (worst by rank order).
        min_coverage: Effective minimum coverage threshold (0-100).
        strict: Whether warnings were promoted to errors.
    """

    files: list[CiCheckResult]
    exit_code: int
    min_coverage: int
    strict: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic dict representation.

        Returns:
            A mapping with top-level ``exit_code``, ``min_coverage``, ``strict``
            and a ``files`` array, with stable key and file ordering.
        """
        return {
            "exit_code": self.exit_code,
            "min_coverage": self.min_coverage,
            "strict": self.strict,
            "files": [
                {
                    "path": f.path,
                    "exit_code": f.exit_code,
                    "schema_errors": list(f.schema_errors),
                    "semantic_warnings": list(f.semantic_warnings),
                    "lint_errors": list(f.lint_errors),
                    "lint_warnings": list(f.lint_warnings),
                    "score": f.score,
                    "coverage": f.coverage,
                    "coverage_below_threshold": f.coverage_below_threshold,
                    "error": f.error,
                    "test_failures": list(f.test_failures),
                    "test_warnings": list(f.test_warnings),
                    "test_errors": list(f.test_errors),
                }
                for f in self.files
            ],
        }

    def to_json(self) -> str:
        """Render the result as a deterministic, byte-stable JSON object."""
        return json.dumps(self.to_dict(), indent=2)

    def to_yaml(self) -> str:
        """Render the result as deterministic, byte-stable YAML."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def to_text(self, use_color: bool = False) -> str:
        """Render a human-readable report.

        Args:
            use_color: When False (default), the output contains no ANSI escapes.

        Returns:
            A deterministic, human-readable per-file and overall report.
        """
        fmt = Formatter(use_color=use_color)
        if not self.files:
            return "No intent.yaml found — nothing to check."

        lines: list[str] = []
        for f in self.files:
            lines.append(fmt.header(f.path))
            if f.error:
                lines.append(fmt.error(f.error))
                lines.append(f"  exit code: {f.exit_code}")
                continue
            for message in f.schema_errors:
                lines.append(fmt.error(message))
            for message in f.lint_errors:
                lines.append(fmt.error(message))
            for message in f.test_failures:
                lines.append(fmt.error(f"test failed: {message}"))
            for message in f.test_errors:
                lines.append(fmt.error(f"test error: {message}"))
            for message in f.semantic_warnings:
                lines.append(fmt.warning(message))
            for message in f.lint_warnings:
                lines.append(fmt.warning(message))
            for message in f.test_warnings:
                lines.append(fmt.warning(f"test warning: {message}"))
            if f.coverage is not None:
                cov_line = f"coverage: {f.coverage}%"
                if f.coverage_below_threshold:
                    cov_line += f" (below threshold {self.min_coverage}%)"
                lines.append(fmt.info(cov_line))
            if f.score is not None:
                lines.append(fmt.info(f"score: ~{f.score:.0f}/100"))
            if f.exit_code == 0:
                lines.append(fmt.success("passed"))
            lines.append(f"  exit code: {f.exit_code}")

        lines.append("")
        lines.append(fmt.header(f"Overall: {_VERDICT[self.exit_code]} (exit {self.exit_code})"))
        return "\n".join(lines)


def run_ci(
    paths: Sequence[str],
    *,
    min_coverage: int = 0,
    strict: bool = False,
    output_format: str = "text",
) -> CiResult:
    """Run validate -> lint -> score -> coverage on each path and aggregate.

    Each path is resolved to files (a file is used directly; a directory is
    globbed for ``**/intent.yaml``; a missing path yields a fatal per-file
    result). For each resolved file the four existing checks are reused and a
    per-file exit code is computed with precedence fatal(3) > error(1) >
    warning(2) > pass(0). The mission-wide exit code is the worst per-file code
    by rank order ``pass(0) < warning(2) < error(1) < fatal(3)``.

    Args:
        paths: Files and/or directories to check.
        min_coverage: Minimum coverage percentage (0-100). 0 disables the check.
        strict: When True, semantic/lint warnings are treated as errors.
        output_format: Retained for API compatibility; ``run_ci`` stays pure and
            rendering is performed via ``CiResult.to_*``.

    Returns:
        A :class:`CiResult` aggregating every resolved file.
    """
    del output_format  # rendering is the caller's responsibility; run_ci is pure.

    files: list[CiCheckResult] = [
        _evaluate_file(display, target, min_coverage=min_coverage, strict=strict)
        for display, target in _resolve_targets(paths)
    ]
    exit_code = _aggregate([f.exit_code for f in files])
    return CiResult(
        files=files,
        exit_code=exit_code,
        min_coverage=min_coverage,
        strict=strict,
    )


def _resolve_targets(paths: Sequence[str]) -> list[tuple[str, Path | None]]:
    """Expand input paths into ordered ``(display_path, file_path)`` targets.

    A file resolves to itself; a directory globs ``**/intent.yaml`` (sorted); a
    missing path resolves to ``(path, None)`` (an unprocessable target). A
    directory with zero matches contributes nothing.
    """
    targets: list[tuple[str, Path | None]] = []
    for raw in paths:
        candidate = Path(raw)
        if candidate.is_file():
            targets.append((str(candidate), candidate))
        elif candidate.is_dir():
            matches = sorted(
                glob.glob(str(candidate / "**" / "intent.yaml"), recursive=True)
            )
            targets.extend((match, Path(match)) for match in matches)
        else:
            targets.append((str(candidate), None))
    return targets


def _evaluate_file(
    display_path: str,
    file_path: Path | None,
    *,
    min_coverage: int,
    strict: bool,
) -> CiCheckResult:
    """Evaluate a single resolved target into a :class:`CiCheckResult`."""
    if file_path is None:
        return _error_result(display_path, f"file not found: {display_path}")

    try:
        intent, schema_errors, semantic_warnings = validate_file(file_path)
    except FileNotFoundError:
        return _error_result(display_path, f"file not found: {display_path}")
    except IntentValidationError as exc:
        return _error_result(display_path, "; ".join(exc.errors) or str(exc))
    except Exception as exc:  # unreadable / malformed YAML — keep CI traceback-free
        return _error_result(display_path, f"could not process file: {exc}")

    try:
        raw_content = file_path.read_text(encoding="utf-8-sig")
    except OSError:
        raw_content = None
    lint_result = lint_intent(
        intent,
        read_source_text(file_path),
        raw_content=raw_content,
    )
    lint_errors = [issue.message for issue in lint_result.errors]
    lint_warnings = [issue.message for issue in lint_result.warnings]

    score = compute_ids(intent).score
    source = resolve_source_for_intent(file_path)
    cov_result = analyze_coverage(
        intent,
        source_path=str(source) if source else None,
    )
    if cov_result.has_source:
        coverage = round(cov_result.overall * 100)
    else:
        coverage = None
    coverage_below_threshold = (
        min_coverage > 0 and coverage is not None and coverage < min_coverage
    )

    test_failures, test_warnings, test_errors = _run_structural_tests(intent, file_path)

    exit_code = _per_file_code(
        error=None,
        schema_errors=schema_errors,
        semantic_warnings=semantic_warnings,
        lint_errors=lint_errors,
        lint_warnings=lint_warnings,
        coverage_below_threshold=coverage_below_threshold,
        test_failures=test_failures,
        test_warnings=test_warnings,
        test_errors=test_errors,
        strict=strict,
    )
    return CiCheckResult(
        path=display_path,
        ok=exit_code == 0,
        exit_code=exit_code,
        schema_errors=schema_errors,
        semantic_warnings=semantic_warnings,
        lint_errors=lint_errors,
        lint_warnings=lint_warnings,
        score=score,
        coverage=coverage,
        coverage_below_threshold=coverage_below_threshold,
        error=None,
        test_failures=test_failures,
        test_warnings=test_warnings,
        test_errors=test_errors,
    )


def _run_structural_tests(
    intent: Any, file_path: Path
) -> tuple[list[str], list[str], list[str]]:
    """Run a sibling ``intent-test.yaml`` (if present) against ``intent``.

    When no sibling test file exists, returns three empty lists so CI behavior is
    unchanged. A schema-invalid test file (or any parse failure) is captured as an
    error message rather than raising, so CI stays traceback-free and continues to
    evaluate other files.

    Args:
        intent: The parsed intent the test cases assert against.
        file_path: The resolved ``intent.yaml`` path; its sibling
            ``intent-test.yaml`` is executed when present.

    Returns:
        ``(test_failures, test_warnings, test_errors)`` — error-severity failure
        messages, warning-severity failure messages, and evaluation/schema error
        messages respectively.
    """
    test_path = file_path.parent / "intent-test.yaml"
    if not test_path.is_file():
        return [], [], []

    try:
        intent_test = parse_intent_test(test_path)
    except IntentTestSchemaError as exc:
        return [], [], [f"invalid intent-test.yaml: {message}" for message in exc.errors]
    except Exception as exc:  # keep CI traceback-free on any unexpected parse failure
        return [], [], [f"could not process intent-test.yaml: {exc}"]

    suite = run_intent_tests(intent, intent_test)
    test_failures: list[str] = []
    test_warnings: list[str] = []
    test_errors: list[str] = []
    for result in suite.tests:
        if result.passed:
            continue
        message = f"{result.name}: {result.message}"
        if result.error:
            test_errors.append(message)
        elif result.severity == "warning":
            test_warnings.append(message)
        else:
            test_failures.append(message)
    return test_failures, test_warnings, test_errors


def _error_result(display_path: str, message: str) -> CiCheckResult:
    """Build a fatal (exit 3) per-file result for an unprocessable file."""
    return CiCheckResult(
        path=display_path,
        ok=False,
        exit_code=3,
        schema_errors=[],
        semantic_warnings=[],
        lint_errors=[],
        lint_warnings=[],
        score=None,
        coverage=None,
        coverage_below_threshold=False,
        error=message,
    )


def _per_file_code(
    *,
    error: str | None,
    schema_errors: list[str],
    semantic_warnings: list[str],
    lint_errors: list[str],
    lint_warnings: list[str],
    coverage_below_threshold: bool,
    strict: bool,
    test_failures: list[str] | None = None,
    test_warnings: list[str] | None = None,
    test_errors: list[str] | None = None,
) -> int:
    """Compute a single file's exit code (highest precedence wins).

    Error-severity test failures and structural-test evaluation/schema errors are
    treated as the error tier (exit ``1``), like ``lint_errors``; warning-severity
    test failures are treated as the warning tier (exit ``2``).
    """
    if error is not None or coverage_below_threshold:
        return 3
    has_errors = (
        bool(schema_errors)
        or bool(lint_errors)
        or bool(test_failures)
        or bool(test_errors)
    )
    has_warnings = bool(semantic_warnings) or bool(lint_warnings) or bool(test_warnings)
    if strict:
        return 1 if (has_errors or has_warnings) else 0
    if has_errors:
        return 1
    if has_warnings:
        return 2
    return 0


def _aggregate(codes: Sequence[int]) -> int:
    """Return the worst code by rank order; 0 for an empty set."""
    if not codes:
        return 0
    return max(codes, key=lambda code: _RANK[code])
