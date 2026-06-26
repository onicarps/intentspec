"""Schema and parser for ``intent-test.yaml`` structural test files.

Defines the :class:`IntentTest` / :class:`TestCase` data model and a validating
parser, :func:`parse_intent_test`. The YAML key ``assert`` is a Python keyword, so
it is mapped to the non-keyword :attr:`TestCase.assertion` attribute on the way in
and back to ``"assert"`` in :meth:`TestCase.to_dict`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

VALID_TYPES = frozenset(
    {
        "constraint_check",
        "presence_check",
        "count_check",
        "regex_check",
        "cross_reference",
    }
)

ASSERT_REQUIRED_TYPES = frozenset({"constraint_check", "count_check", "regex_check"})

VALID_SEVERITIES = frozenset({"error", "warning"})

_TOP_LEVEL_FIELDS = frozenset({"name", "description", "tests"})

_CASE_FIELDS = frozenset({"name", "type", "description", "assert", "field", "severity"})


class IntentTestSchemaError(Exception):
    """Raised when an ``intent-test.yaml`` file fails schema validation.

    Mirrors :class:`intentspec.models.intent.IntentValidationError`: it carries a
    list of human-readable messages that name the offending field/test so the CLI
    can render actionable output.
    """

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"intent-test.yaml schema validation failed with {len(errors)} error(s)")


@dataclass
class TestCase:
    """A single structural test case.

    Attributes:
        name: Required identifier for the case.
        type: One of the five allowed assertion kinds (see :data:`VALID_TYPES`).
        description: Optional human-readable description.
        assertion: The assertion DSL string. The YAML key is ``assert``; this
            non-keyword attribute holds its value.
        field: Optional dotted field path the assertion operates on.
        severity: ``"error"`` (default) or ``"warning"``.
    """

    __test__ = False  # not a pytest test class despite the "Test" prefix

    name: str
    type: str
    description: str = ""
    assertion: str = ""
    field: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to a dict, mapping ``assertion`` to the YAML key ``assert``."""
        result: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
        }
        if self.description:
            result["description"] = self.description
        if self.assertion:
            result["assert"] = self.assertion
        if self.field is not None:
            result["field"] = self.field
        result["severity"] = self.severity
        return result


@dataclass
class IntentTest:
    """A parsed ``intent-test.yaml`` file.

    Attributes:
        name: Required suite name.
        description: Optional suite description.
        tests: List of :class:`TestCase` (may be empty).
    """

    name: str
    description: str = ""
    tests: list[TestCase] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize back to a dict, round-tripping each case via :meth:`TestCase.to_dict`."""
        return {
            "name": self.name,
            "description": self.description,
            "tests": [tc.to_dict() for tc in self.tests],
        }


def parse_intent_test(path: Path | str) -> IntentTest:
    """Load and validate an ``intent-test.yaml`` file.

    Args:
        path: Path to the test file.

    Returns:
        A validated :class:`IntentTest`.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        IntentTestSchemaError: If the content violates the schema (empty/non-dict
            top level, missing/invalid fields, unknown keys, etc.).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"intent-test.yaml not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    errors: list[str] = []

    if raw is None:
        raise IntentTestSchemaError(["File is empty"])
    if not isinstance(raw, dict):
        raise IntentTestSchemaError(
            [f"Top-level content must be a mapping, got {type(raw).__name__}"]
        )

    unknown_top = sorted(set(raw) - _TOP_LEVEL_FIELDS)
    for key in unknown_top:
        errors.append(f"Unknown top-level field: '{key}'")

    name = raw.get("name")
    if name is None:
        errors.append("Missing required top-level field: 'name'")
    elif not isinstance(name, str):
        errors.append("Top-level field 'name' must be a string")

    description = raw.get("description", "")
    if not isinstance(description, str):
        errors.append("Top-level field 'description' must be a string")
        description = ""

    raw_tests = raw.get("tests", [])
    if raw_tests is None:
        raw_tests = []
    if not isinstance(raw_tests, list):
        errors.append("Top-level field 'tests' must be a list")
        raw_tests = []

    cases: list[TestCase] = []
    for index, raw_case in enumerate(raw_tests):
        cases.append(_parse_case(index, raw_case, errors))

    if errors:
        raise IntentTestSchemaError(errors)

    return IntentTest(
        name=name,
        description=description,
        tests=cases,
    )


def _parse_case(index: int, raw_case: Any, errors: list[str]) -> TestCase:
    """Validate and build a single :class:`TestCase`, accumulating errors.

    Returns a best-effort :class:`TestCase`; the accumulated ``errors`` (if any)
    will cause :func:`parse_intent_test` to raise before the result is used.
    """
    label = f"test[{index}]"
    if not isinstance(raw_case, dict):
        errors.append(f"{label}: each test case must be a mapping")
        return TestCase(name="", type="")

    case_name = raw_case.get("name")
    if case_name:
        label = f"test[{index}] '{case_name}'"

    unknown_case = sorted(set(raw_case) - _CASE_FIELDS)
    for key in unknown_case:
        errors.append(f"{label}: unknown field '{key}'")

    if case_name is None:
        errors.append(f"{label}: missing required field 'name'")
        case_name = ""
    elif not isinstance(case_name, str):
        errors.append(f"{label}: field 'name' must be a string")
        case_name = ""

    case_type = raw_case.get("type")
    if case_type is None:
        errors.append(f"{label}: missing required field 'type'")
        case_type = ""
    elif case_type not in VALID_TYPES:
        errors.append(
            f"{label}: invalid 'type' value '{case_type}'; "
            f"must be one of {sorted(VALID_TYPES)}"
        )

    assertion = raw_case.get("assert", "")
    if assertion is None:
        assertion = ""
    if not isinstance(assertion, str):
        errors.append(f"{label}: field 'assert' must be a string")
        assertion = ""

    if case_type in ASSERT_REQUIRED_TYPES and not assertion.strip():
        errors.append(f"{label}: field 'assert' is required (non-empty) for type '{case_type}'")

    case_field = raw_case.get("field")
    if case_field is not None and not isinstance(case_field, str):
        errors.append(f"{label}: field 'field' must be a string")
        case_field = None

    severity = raw_case.get("severity", "error")
    if severity is None:
        severity = "error"
    if severity not in VALID_SEVERITIES:
        errors.append(
            f"{label}: invalid 'severity' value '{severity}'; must be 'error' or 'warning'"
        )
        severity = "error"

    description = raw_case.get("description", "")
    if not isinstance(description, str):
        errors.append(f"{label}: field 'description' must be a string")
        description = ""

    return TestCase(
        name=case_name,
        type=case_type,
        description=description,
        assertion=assertion,
        field=case_field,
        severity=severity,
    )
