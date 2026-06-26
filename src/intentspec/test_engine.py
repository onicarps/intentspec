"""Structural assertion engine for ``intent-test.yaml`` suites.

Evaluates each :class:`~intentspec.test_schema.TestCase` against a parsed
:class:`~intentspec.models.intent.Intent` and aggregates the outcomes into a
:class:`TestSuiteResult`.

Security invariant: assertion (``assert``) strings are a small, fixed DSL parsed
**structurally** with :mod:`re` / string operations. They are NEVER passed to
``eval``/``exec``/``compile``; a crafted code-like payload simply fails to match a
grammar and is reported as an error. All five assertion grammars are documented in
the docstring of the function that implements them.

Field-path mapping (intent.yaml dotted path -> :class:`Intent` attribute):
    ``non_negotiables`` -> ``non_negotiables``
    ``constraints``     -> ``constraints``
    ``boundaries``      -> ``boundaries``
    ``failure_modes``   -> ``failure_modes``
    ``goals``           -> ``goals``
    ``tools.allowed``   -> ``tools_allowed``
    ``tools.denied``    -> ``tools_denied``
    ``escalation``      -> ``escalation``
    ``sub_agents``      -> ``sub_agents``
    ``extends``         -> ``extends``
    ``metadata.owner``  -> ``metadata.owner``
    ``metadata.status`` -> ``metadata.status``
    ``agent.name``      -> ``agent_name``
    ``agent.type``      -> ``agent_type``
    ``agent.description`` -> ``agent_description``
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from intentspec.models.intent import Intent

_OPERATORS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}

_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "non_negotiables": ("non_negotiables",),
    "constraints": ("constraints",),
    "boundaries": ("boundaries",),
    "failure_modes": ("failure_modes",),
    "goals": ("goals",),
    "tools.allowed": ("tools_allowed",),
    "tools.denied": ("tools_denied",),
    "tools_allowed": ("tools_allowed",),
    "tools_denied": ("tools_denied",),
    "escalation": ("escalation",),
    "sub_agents": ("sub_agents",),
    "extends": ("extends",),
    "metadata.owner": ("metadata", "owner"),
    "metadata.status": ("metadata", "status"),
    "metadata.created": ("metadata", "created"),
    "metadata.updated": ("metadata", "updated"),
    "agent.name": ("agent_name",),
    "agent.type": ("agent_type",),
    "agent.description": ("agent_description",),
}

_COUNT_RE = re.compile(
    r"""^len\(\s*
        (?P<collection>[\w.]+)
        (?:\s*\[\s*(?P<key>\w+)\s*=\s*(?P<quote>['"])(?P<value>[^'"]*)(?P=quote)\s*\])?
        \s*\)\s*
        (?P<op>>=|<=|==|!=|>|<)\s*
        (?P<operand>\d+)\s*$""",
    re.VERBOSE,
)

_CONSTRAINT_RE = re.compile(
    r"^(?P<left>[\w.]+)\s*(?:∩|intersect)\s*(?P<right>[\w.]+)\s*==\s*(?:∅|empty)\s*$"
)

_SUBSET_RE = re.compile(
    r"^(?:every\s+\w+\s+in\s+)?(?P<left>[\w.]+)\s+subset\s+(?P<right>[\w.]+)\s*$"
)

_CONDITIONAL_RE = re.compile(
    r"^(?P<target>[\w.]+)\s+non-empty\s+when\s+(?P<guard>[\w.]+)\s+set\s*$"
)

_PRESENCE_RE = re.compile(
    r"^(?P<field>[\w.]+)\s+is\s+not\s+(?:null|empty|none)\s*$", re.IGNORECASE
)


class _Unresolved:
    """Sentinel for a field path that does not resolve to an Intent attribute."""


_UNRESOLVED = _Unresolved()


@dataclass
class TestResult:
    """Outcome of a single :class:`~intentspec.test_schema.TestCase`.

    Attributes:
        name: The test case name.
        passed: ``True`` if the assertion held.
        message: Human-readable outcome (names expected-vs-found on failure).
        severity: ``"error"`` or ``"warning"`` (from the test case).
        duration_ms: Wall-clock evaluation time, measured with
            :func:`time.perf_counter`.
        error: ``True`` if the case could not be evaluated (unparseable assertion,
            malformed regex, unknown field path). Error results count toward the
            suite ``errors`` total rather than ``failed``/``warnings``.
    """

    __test__ = False  # not a pytest test class despite the "Test" prefix

    name: str
    passed: bool
    message: str
    severity: str = "error"
    duration_ms: float = 0.0
    error: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-serializable dict."""
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class TestSuiteResult:
    """Aggregated outcome of running an :class:`IntentTest` suite.

    Attributes:
        tests: Per-case :class:`TestResult` list, in evaluation order.
        passed: Number of cases that passed.
        failed: Number of error-severity cases that failed (non-error evaluations).
        errors: Number of cases that could not be evaluated.
        warnings: Number of warning-severity cases that failed.
        total_duration_ms: Sum of per-case ``duration_ms`` values.
    """

    __test__ = False  # not a pytest test class despite the "Test" prefix

    tests: list[TestResult] = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    errors: int = 0
    warnings: int = 0
    total_duration_ms: float = 0.0

    def recount(self) -> None:
        """Recompute aggregate counts from :attr:`tests`."""
        self.passed = sum(1 for t in self.tests if t.passed)
        self.errors = sum(1 for t in self.tests if t.error)
        self.failed = sum(
            1 for t in self.tests if not t.passed and not t.error and t.severity != "warning"
        )
        self.warnings = sum(
            1 for t in self.tests if not t.passed and not t.error and t.severity == "warning"
        )
        self.total_duration_ms = sum(t.duration_ms for t in self.tests)

    def to_text(self) -> str:
        """Render a non-empty, human-readable summary consistent with the counts."""
        lines = [
            f"  {self.passed} passed, {self.failed} failed, "
            f"{self.warnings} warning(s), {self.errors} error(s) "
            f"in {self.total_duration_ms:.2f}ms"
        ]
        for t in self.tests:
            if t.passed:
                tag = "PASS"
            elif t.error:
                tag = "ERROR"
            elif t.severity == "warning":
                tag = "WARN"
            else:
                tag = "FAIL"
            lines.append(f"  [{tag}] {t.name}: {t.message}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-serializable dict with counts and a per-test list."""
        return {
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "warnings": self.warnings,
            "total": len(self.tests),
            "total_duration_ms": self.total_duration_ms,
            "tests": [t.to_dict() for t in self.tests],
        }


def run_intent_tests(intent: Intent, intent_test: "IntentTestLike") -> TestSuiteResult:
    """Evaluate every test case in ``intent_test`` against ``intent``.

    Each case is timed independently; a failure or evaluation error in one case is
    captured in its :class:`TestResult` and never aborts the suite.

    Args:
        intent: The parsed intent to assert against.
        intent_test: The parsed test suite (``IntentTest``) whose ``tests`` list
            holds the cases to evaluate.

    Returns:
        A :class:`TestSuiteResult` with per-case results and aggregate counts.
    """
    suite = TestSuiteResult()
    for case in intent_test.tests:
        start = time.perf_counter()
        try:
            passed, message, is_error = _evaluate_case(intent, case)
        except Exception as exc:  # defensive: no single case may abort the suite
            passed, message, is_error = False, f"Evaluation error: {exc}", True
        duration_ms = (time.perf_counter() - start) * 1000.0
        suite.tests.append(
            TestResult(
                name=case.name,
                passed=passed,
                message=message,
                severity=case.severity,
                duration_ms=duration_ms,
                error=is_error,
            )
        )
    suite.recount()
    return suite


def _evaluate_case(intent: Intent, case: "TestCaseLike") -> tuple[bool, str, bool]:
    """Dispatch a single case to its assertion-type handler.

    Returns:
        ``(passed, message, is_error)``.
    """
    handler = {
        "presence_check": _eval_presence,
        "count_check": _eval_count,
        "constraint_check": _eval_constraint,
        "regex_check": _eval_regex,
        "cross_reference": _eval_cross_reference,
    }.get(case.type)
    if handler is None:
        return False, f"Unknown assertion type: '{case.type}'", True
    return handler(intent, case)


def _eval_presence(intent: Intent, case: "TestCaseLike") -> tuple[bool, str, bool]:
    """presence_check: a field exists and is non-empty.

    The target field comes from ``field`` (a dotted path) or, if absent, from an
    ``assert`` of the form ``<field> is not null`` / ``<field> is not empty``.
    Passes when the resolved value is present and non-empty.
    """
    path = case.field
    if not path and case.assertion:
        match = _PRESENCE_RE.match(case.assertion.strip())
        if match:
            path = match.group("field")
    if not path:
        return False, "presence_check requires a 'field' or a parseable assertion", True

    value = _resolve_field(intent, path)
    if value is _UNRESOLVED:
        return False, f"Unknown field path: '{path}'", True
    if _is_non_empty(value):
        return True, f"Field '{path}' is present and non-empty", False
    return False, f"Field '{path}' is absent or empty", False


def _eval_count(intent: Intent, case: "TestCaseLike") -> tuple[bool, str, bool]:
    """count_check: collection cardinality versus an integer.

    Grammar: ``len(<collection>[<key>='<value>']) <op> <int>`` where the filter is
    optional and ``<op>`` is one of ``>=``, ``<=``, ``>``, ``<``, ``==``, ``!=``.
    The optional filter counts only items whose attribute ``<key>`` equals
    ``<value>`` (e.g. ``len(non_negotiables[severity='hard']) >= 1``).
    """
    match = _COUNT_RE.match(case.assertion.strip())
    if not match:
        return False, f"Unparseable count_check assertion: '{case.assertion}'", True

    collection_path = match.group("collection")
    value = _resolve_field(intent, collection_path)
    if value is _UNRESOLVED:
        return False, f"Unknown field path: '{collection_path}'", True

    items = _as_list(value)
    key = match.group("key")
    if key is not None:
        wanted = match.group("value")
        items = [it for it in items if str(getattr(it, key, _sentinel_get(it, key))) == wanted]

    count = len(items)
    op = match.group("op")
    operand = int(match.group("operand"))
    if _OPERATORS[op](count, operand):
        return True, f"len({collection_path})={count} {op} {operand}", False
    return False, f"Expected len({collection_path}) {op} {operand}, found {count}", False


def _eval_constraint(intent: Intent, case: "TestCaseLike") -> tuple[bool, str, bool]:
    """constraint_check: a set relationship over two collections.

    Grammar (intersection-empty), accepting Unicode or ASCII spellings:
    ``<A> ∩ <B> == ∅`` or ``<A> intersect <B> == empty``. The collections are
    reduced to their element names (tool names, sub-agent strings, etc.); the check
    passes when the two name-sets are disjoint and fails naming the overlap.
    """
    match = _CONSTRAINT_RE.match(case.assertion.strip())
    if not match:
        return False, f"Unparseable constraint_check assertion: '{case.assertion}'", True

    left_path, right_path = match.group("left"), match.group("right")
    left_val = _resolve_field(intent, left_path)
    right_val = _resolve_field(intent, right_path)
    if left_val is _UNRESOLVED:
        return False, f"Unknown field path: '{left_path}'", True
    if right_val is _UNRESOLVED:
        return False, f"Unknown field path: '{right_path}'", True

    overlap = _as_name_set(left_val) & _as_name_set(right_val)
    if not overlap:
        return True, f"{left_path} ∩ {right_path} is empty", False
    return False, f"{left_path} ∩ {right_path} overlaps on: {sorted(overlap)}", False


def _eval_regex(intent: Intent, case: "TestCaseLike") -> tuple[bool, str, bool]:
    """regex_check: a pattern (``assert``) against a string field (``field``).

    The ``field`` is resolved to a string and matched with :func:`re.search`
    (anchored patterns therefore behave as full matches). A malformed pattern is
    captured as an error, not a crash.
    """
    if not case.field:
        return False, "regex_check requires a 'field'", True
    value = _resolve_field(intent, case.field)
    if value is _UNRESOLVED:
        return False, f"Unknown field path: '{case.field}'", True
    if value is None:
        return False, f"Field '{case.field}' is empty; nothing to match", False

    target = value if isinstance(value, str) else str(value)
    try:
        pattern = re.compile(case.assertion)
    except re.error as exc:
        return False, f"Malformed regex '{case.assertion}': {exc}", True

    if pattern.search(target):
        return True, f"'{target}' matches /{case.assertion}/", False
    return False, f"'{target}' does not match /{case.assertion}/", False


def _eval_cross_reference(intent: Intent, case: "TestCaseLike") -> tuple[bool, str, bool]:
    """cross_reference: a referential relationship between two fields.

    Two documented grammars are supported:

    * Subset: ``[every <var> in ]<A> subset <B>`` — every element name of
      collection ``A`` must appear in collection ``B``; fails naming the
      unresolved members.
    * Conditional presence: ``<A> non-empty when <B> set`` — if collection/field
      ``B`` is non-empty then ``A`` must be non-empty; fails naming ``A``.
    """
    assertion = case.assertion.strip()
    if not assertion:
        return False, "cross_reference requires an assertion grammar", True

    cond = _CONDITIONAL_RE.match(assertion)
    if cond:
        target_path, guard_path = cond.group("target"), cond.group("guard")
        target_val = _resolve_field(intent, target_path)
        guard_val = _resolve_field(intent, guard_path)
        if target_val is _UNRESOLVED:
            return False, f"Unknown field path: '{target_path}'", True
        if guard_val is _UNRESOLVED:
            return False, f"Unknown field path: '{guard_path}'", True
        if not _is_non_empty(guard_val):
            return True, f"'{guard_path}' not set; '{target_path}' not required", False
        if _is_non_empty(target_val):
            return True, f"'{target_path}' is non-empty as required by '{guard_path}'", False
        return False, f"'{target_path}' is empty but '{guard_path}' is set", False

    subset = _SUBSET_RE.match(assertion)
    if subset:
        left_path, right_path = subset.group("left"), subset.group("right")
        left_val = _resolve_field(intent, left_path)
        right_val = _resolve_field(intent, right_path)
        if left_val is _UNRESOLVED:
            return False, f"Unknown field path: '{left_path}'", True
        if right_val is _UNRESOLVED:
            return False, f"Unknown field path: '{right_path}'", True
        missing = _as_name_set(left_val) - _as_name_set(right_val)
        if not missing:
            return True, f"every member of {left_path} is in {right_path}", False
        return False, f"{left_path} members missing from {right_path}: {sorted(missing)}", False

    return False, f"Unparseable cross_reference assertion: '{case.assertion}'", True


def _resolve_field(intent: Intent, path: str) -> Any:
    """Resolve a dotted intent.yaml field path to its :class:`Intent` value.

    Returns :data:`_UNRESOLVED` if the path is not a known/derivable attribute.
    """
    attrs = _FIELD_MAP.get(path)
    if attrs is None:
        attrs = _derive_attrs(path)
    if attrs is None:
        return _UNRESOLVED

    current: Any = intent
    for attr in attrs:
        if not hasattr(current, attr):
            return _UNRESOLVED
        current = getattr(current, attr)
    return current


def _derive_attrs(path: str) -> tuple[str, ...] | None:
    """Best-effort mapping for paths not in :data:`_FIELD_MAP`."""
    if "." not in path:
        return (path,)
    head, _, tail = path.partition(".")
    if head in {"tools", "agent"}:
        return (f"{head}_{tail}",)
    if head == "metadata":
        return ("metadata", tail)
    return None


def _is_non_empty(value: Any) -> bool:
    """A value is present and non-empty (None / empty container / blank string are empty)."""
    if value is None or value is _UNRESOLVED:
        return False
    if isinstance(value, (list, tuple, set, dict, str)):
        if isinstance(value, str):
            return bool(value.strip())
        return len(value) > 0
    return True


def _as_list(value: Any) -> list[Any]:
    """Coerce a resolved value into a list for cardinality checks."""
    if value is None or value is _UNRESOLVED:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _as_name_set(value: Any) -> set[str]:
    """Reduce a collection to a set of element names for set relations.

    Objects with a ``name`` attribute contribute their name; strings contribute
    themselves; anything else contributes its ``str()`` form.
    """
    names: set[str] = set()
    for item in _as_list(value):
        if isinstance(item, str):
            names.add(item)
        elif hasattr(item, "name"):
            names.add(item.name)
        else:
            names.add(str(item))
    return names


def _sentinel_get(item: Any, key: str) -> Any:
    """Fallback accessor for dict-shaped items in filtered count checks."""
    if isinstance(item, dict):
        return item.get(key)
    return None


# Lightweight structural type aliases for the parsed schema objects. Importing the
# concrete classes is unnecessary at runtime; duck typing on .tests / .type /
# .assertion / .field / .severity / .name is sufficient and avoids a hard cycle.
IntentTestLike = Any
TestCaseLike = Any
