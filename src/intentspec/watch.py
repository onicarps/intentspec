"""File watching and auto-testing for intent.yaml changes.

Implements a polling-based file watcher that avoids external dependencies.
Runs validate + test on intent.yaml changes and reports results.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from intentspec.spec.validate import validate_file
from intentspec.models.intent import IntentValidationError
from intentspec.lint import lint_intent
from intentspec.source_resolve import read_source_text
from intentspec.test_engine import run_intent_tests
from intentspec.test_schema import IntentTestSchemaError, parse_intent_test


@dataclass
class WatchResult:
    """Result of a single watch iteration."""

    path: Path
    valid: bool
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_text(self) -> str:
        """Return human-readable text output."""
        status = "✓ PASS" if self.valid else "✗ FAIL"
        lines = [f"{self.path.name}: {status}"]
        if self.tests_run > 0:
            lines.append(f"  Tests: {self.tests_passed}/{self.tests_run} passed")
        if self.errors:
            for e in self.errors[:3]:
                lines.append(f"  Error: {e}")
        if self.warnings:
            for w in self.warnings[:3]:
                lines.append(f"  Warning: {w}")
        return "\n".join(lines)


def run_watch_cycle(intent_path: Path) -> WatchResult:
    """Run validate + lint + test on a single intent.yaml file.

    Returns a WatchResult with pass/fail status and any errors/warnings.
    """
    result = WatchResult(path=intent_path, valid=True)

    # Validate
    try:
        intent, schema_errors, semantic_warnings = validate_file(intent_path)
        if schema_errors:
            result.valid = False
            result.errors.extend(schema_errors)

        for warning in semantic_warnings:
            result.warnings.append(warning)

        try:
            raw_content = intent_path.read_text(encoding="utf-8-sig")
        except OSError:
            raw_content = None
        lint_result = lint_intent(
            intent,
            read_source_text(intent_path),
            raw_content=raw_content,
        )
        for issue in lint_result.issues:
            msg = f"{issue.rule}: {issue.message}"
            if issue.severity == "warning":
                result.warnings.append(msg)
            else:
                result.errors.append(msg)
                result.valid = False

        # Test if intent-test.yaml exists
        test_path = intent_path.parent / "intent-test.yaml"
        if test_path.is_file():
            try:
                intent_test = parse_intent_test(test_path)
                suite = run_intent_tests(intent, intent_test)
                result.tests_run = len(suite.tests)
                result.tests_passed = suite.passed
                result.tests_failed = suite.failed

                # Extract error/warning messages from failed tests
                for t in suite.tests:
                    if not t.passed and t.severity == "error":
                        result.errors.append(t.message)
                        result.valid = False
                    elif not t.passed and t.severity == "warning":
                        result.warnings.append(t.message)

            except IntentTestSchemaError as e:
                result.valid = False
                result.errors.extend(e.errors)

    except IntentValidationError as e:
        result.valid = False
        result.errors.extend(e.errors)
    except Exception as e:
        result.valid = False
        result.errors.append(str(e))

    return result


def watch_exit_code(result: WatchResult) -> int:
    """Map a watch result to standard IntentSpec exit codes."""
    if result.errors:
        return 1
    if result.warnings:
        return 2
    return 0


def watch_directory(path: Path, callback: Callable[[WatchResult], None], poll_interval: float = 0.5) -> None:
    """Poll path for intent.yaml changes, call callback on change.

    Uses stat-based polling to detect changes. Terminates on KeyboardInterrupt.
    """
    intent_path = path / "intent.yaml" if path.is_dir() else path

    if not intent_path.is_file():
        raise FileNotFoundError(f"No intent.yaml found at {path}")

    last_mtime = intent_path.stat().st_mtime

    try:
        while True:
            time.sleep(poll_interval)
            try:
                current_mtime = intent_path.stat().st_mtime
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    result = run_watch_cycle(intent_path)
                    callback(result)
            except FileNotFoundError:
                # File was deleted, wait for it to reappear
                pass
    except KeyboardInterrupt:
        sys.exit(0)