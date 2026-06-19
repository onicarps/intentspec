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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import yaml

from intentspec.coverage import analyze_coverage
from intentspec.lint import lint_intent
from intentspec.models.intent import IntentValidationError
from intentspec.score.ids import compute_ids
from intentspec.spec.formatter import Formatter
from intentspec.spec.validate import validate_file

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
            for message in f.semantic_warnings:
                lines.append(fmt.warning(message))
            for message in f.lint_warnings:
                lines.append(fmt.warning(message))
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

    lint_result = lint_intent(intent)
    lint_errors = [issue.message for issue in lint_result.errors]
    lint_warnings = [issue.message for issue in lint_result.warnings]

    score = compute_ids(intent).score
    coverage = round(analyze_coverage(intent, source_path=str(file_path)).overall * 100)
    coverage_below_threshold = min_coverage > 0 and coverage < min_coverage

    exit_code = _per_file_code(
        error=None,
        schema_errors=schema_errors,
        semantic_warnings=semantic_warnings,
        lint_errors=lint_errors,
        lint_warnings=lint_warnings,
        coverage_below_threshold=coverage_below_threshold,
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
    )


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
) -> int:
    """Compute a single file's exit code (highest precedence wins)."""
    if error is not None or coverage_below_threshold:
        return 3
    has_errors = bool(schema_errors) or bool(lint_errors)
    has_warnings = bool(semantic_warnings) or bool(lint_warnings)
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
