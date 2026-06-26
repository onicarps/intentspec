"""GitHub Actions status output for IntentSpec.

Aggregates validate, lint, and structural test results into a single JSON-friendly
payload suitable for CI status checks.
"""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from intentspec.lint import lint_intent
from intentspec.models.intent import IntentValidationError
from intentspec.source_resolve import read_source_text
from intentspec.spec.validate import validate_file
from intentspec.test_engine import run_intent_tests
from intentspec.test_schema import IntentTestSchemaError, parse_intent_test

_RANK: dict[int, int] = {0: 0, 2: 1, 1: 2, 3: 3}


@dataclass
class StatusIssue:
    """A single issue surfaced by a status check."""

    file: str
    severity: str
    message: str
    check: str


@dataclass
class StatusResult:
    """Aggregated status for one or more intent.yaml files."""

    passed: bool
    exit_code: int
    issues: list[StatusIssue] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "exit_code": self.exit_code,
            "issues": [
                {
                    "file": issue.file,
                    "severity": issue.severity,
                    "message": issue.message,
                    "check": issue.check,
                }
                for issue in self.issues
            ],
            "checks": dict(self.checks),
        }


def _resolve_files(paths: Sequence[str]) -> list[tuple[str, Path | None]]:
    targets: list[tuple[str, Path | None]] = []
    for raw in paths:
        candidate = Path(raw)
        if candidate.is_file():
            targets.append((str(candidate), candidate))
        elif candidate.is_dir():
            matches = sorted(glob.glob(str(candidate / "**" / "intent.yaml"), recursive=True))
            targets.extend((match, Path(match)) for match in matches)
        else:
            targets.append((str(candidate), None))
    return targets


def _check_label(has_errors: bool, has_warnings: bool, skipped: bool = False) -> str:
    if skipped:
        return "skip"
    if has_errors:
        return "fail"
    if has_warnings:
        return "warning"
    return "pass"


def evaluate_status_file(file_path: Path) -> tuple[int, list[StatusIssue], dict[str, str]]:
    """Evaluate validate, lint, and test for a single intent.yaml."""
    issues: list[StatusIssue] = []
    display = str(file_path)
    validate_errors = False
    validate_warnings = False
    lint_errors = False
    lint_warnings = False
    test_errors = False
    test_warnings = False
    test_skipped = True

    try:
        intent, schema_errors, semantic_warnings = validate_file(file_path)
    except IntentValidationError as exc:
        for message in exc.errors:
            issues.append(StatusIssue(display, "error", message, "validate"))
        return 1, issues, {"validate": "fail", "lint": "skip", "test": "skip"}
    except Exception as exc:
        issues.append(StatusIssue(display, "error", str(exc), "validate"))
        return 1, issues, {"validate": "fail", "lint": "skip", "test": "skip"}

    for message in schema_errors:
        validate_errors = True
        issues.append(StatusIssue(display, "error", message, "validate"))
    for message in semantic_warnings:
        validate_warnings = True
        issues.append(StatusIssue(display, "warning", message, "validate"))

    try:
        raw_content = file_path.read_text(encoding="utf-8-sig")
    except OSError:
        raw_content = None
    lint_result = lint_intent(
        intent,
        read_source_text(file_path),
        raw_content=raw_content,
    )
    for issue in lint_result.errors:
        lint_errors = True
        issues.append(StatusIssue(display, "error", issue.message, "lint"))
    for issue in lint_result.warnings:
        lint_warnings = True
        issues.append(StatusIssue(display, "warning", issue.message, "lint"))

    test_path = file_path.parent / "intent-test.yaml"
    if test_path.is_file():
        test_skipped = False
        try:
            intent_test = parse_intent_test(test_path)
            suite = run_intent_tests(intent, intent_test)
            for test_result in suite.tests:
                if test_result.passed:
                    continue
                if test_result.error or test_result.severity != "warning":
                    test_errors = True
                    issues.append(StatusIssue(display, "error", test_result.message, "test"))
                else:
                    test_warnings = True
                    issues.append(
                        StatusIssue(display, "warning", test_result.message, "test")
                    )
        except IntentTestSchemaError as exc:
            test_skipped = False
            test_errors = True
            for message in exc.errors:
                issues.append(StatusIssue(display, "error", message, "test"))
        except Exception as exc:
            test_skipped = False
            test_errors = True
            issues.append(StatusIssue(display, "error", str(exc), "test"))

    checks = {
        "validate": _check_label(validate_errors, validate_warnings),
        "lint": _check_label(lint_errors, lint_warnings),
        "test": _check_label(test_errors, test_warnings, skipped=test_skipped),
    }

    if validate_errors or lint_errors or test_errors:
        exit_code = 1
    elif validate_warnings or lint_warnings or test_warnings:
        exit_code = 2
    else:
        exit_code = 0
    return exit_code, issues, checks


def run_status(paths: Sequence[str]) -> StatusResult:
    """Run validate + lint + test and aggregate a status payload."""
    targets = _resolve_files(paths)
    if not targets:
        return StatusResult(
            passed=False,
            exit_code=3,
            issues=[StatusIssue(".", "error", "no intent.yaml found", "validate")],
            checks={"validate": "fail", "lint": "skip", "test": "skip"},
        )

    all_issues: list[StatusIssue] = []
    exit_codes: list[int] = []
    aggregate_checks: dict[str, str] = {"validate": "pass", "lint": "pass", "test": "pass"}

    for display, file_path in targets:
        if file_path is None:
            exit_codes.append(3)
            all_issues.append(StatusIssue(display, "error", f"file not found: {display}", "validate"))
            aggregate_checks["validate"] = "fail"
            continue

        code, issues, checks = evaluate_status_file(file_path)
        exit_codes.append(code)
        all_issues.extend(issues)
        for name, label in checks.items():
            if label == "fail":
                aggregate_checks[name] = "fail"
            elif label == "warning" and aggregate_checks[name] == "pass":
                aggregate_checks[name] = "warning"
            elif label == "skip" and aggregate_checks[name] == "pass":
                aggregate_checks[name] = "skip"

    exit_code = max(exit_codes, key=lambda code: _RANK.get(code, 0)) if exit_codes else 3
    return StatusResult(
        passed=exit_code == 0,
        exit_code=exit_code,
        issues=all_issues,
        checks=aggregate_checks,
    )