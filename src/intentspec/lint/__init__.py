"""Linting rules engine for IntentSpec — v2 (15+ rules)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from intentspec.models.intent import Intent


@dataclass
class LintIssue:
    """A single lint issue found in an intent spec."""
    rule: str
    severity: str  # "error" or "warning"
    message: str
    field: str | None = None

    def to_text(self) -> str:
        tag = "ERROR" if self.severity == "error" else "WARN"
        loc = f" ({self.field})" if self.field else ""
        return f"  [{tag}] {self.rule}{loc}: {self.message}"


@dataclass
class LintResult:
    """Result of linting an intent spec."""
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def is_clean(self) -> bool:
        return self.error_count == 0 and self.warning_count == 0

    def to_text(self) -> str:
        if not self.issues:
            return "  No issues found — clean intent spec."

        lines = [f"  {self.error_count} error(s), {self.warning_count} warning(s):"]
        for issue in self.issues:
            lines.append(issue.to_text())
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "clean": self.error_count == 0 and self.warning_count == 0,
            "errors": self.error_count,
            "warnings": self.warning_count,
            "issues": [
                {"rule": i.rule, "severity": i.severity, "message": i.message, "field": i.field}
                for i in self.issues
            ],
        }


# --- Rule: agent-description ---

def _check_agent_description(intent: Intent) -> LintIssue | None:
    if not intent.agent_description or len(intent.agent_description.strip()) < 10:
        return LintIssue("agent-description", "warning",
                        "Agent description is too short (<10 chars)")
    if len(intent.agent_description) > 200:
        return LintIssue("agent-description-length", "warning",
                        f"Agent description exceeds 200 chars ({len(intent.agent_description)})",
                        field="agent.description")
    return None


# --- Rule: goals-required ---

def _check_goals_required(intent: Intent) -> LintIssue | None:
    if not intent.goals:
        return LintIssue("goals-required", "error",
                        "No goals defined. Agent needs at least one goal.",
                        field="intent.goals")
    return None


# --- Rule: goal-description-length ---

RE_PLACEHOLDER = re.compile(r"^(todo|fixme|tbd|placeholder|xxx|test|temp)\s*$", re.IGNORECASE)
_DISABLE_RE = re.compile(r"#\s*intentspec:\s*disable=([a-z0-9-]+)", re.IGNORECASE)


def parse_disabled_rules(content: str) -> set[str]:
    """Parse per-line rule disables from intent.yaml comments."""
    return {m.group(1).lower() for m in _DISABLE_RE.finditer(content)}

def _check_goal_description_length(intent: Intent) -> list[LintIssue]:
    issues = []
    for i, goal in enumerate(intent.goals):
        if len(goal.description) < 10:
            issues.append(LintIssue("goal-description-length", "warning",
                                   f"Goal {i+1} description is too short",
                                   field=f"intent.goals[{i}]"))
        if RE_PLACEHOLDER.match(goal.description):
            issues.append(LintIssue("empty-description", "warning",
                                   f"Goal {i+1} has placeholder text: \"{goal.description}\"",
                                   field=f"intent.goals[{i}].description"))
    return issues


# --- Rule: constraint-enforceable ---

def _check_constraint_enforceable(intent: Intent) -> list[LintIssue]:
    issues = []
    for i, c in enumerate(intent.constraints):
        if c.enforceable:
            rule_lower = c.rule.lower()
            # Check if the constraint text looks auto-checkable
            has_checkable_indicator = any(
                kw in rule_lower
                for kw in ["must not", "must", "only", "never", "always", "required"]
            )
            if not has_checkable_indicator:
                issues.append(LintIssue("unenforceable-constraint", "warning",
                                       f"Constraint {i+1} marked enforceable but text doesn\'t look auto-checkable",
                                       field=f"intent.constraints[{i}]"))
    return issues


# --- Rule: tool-rationale ---

def _check_tool_rationale(intent: Intent) -> list[LintIssue]:
    issues = []
    for tool in intent.tools_allowed:
        if not tool.rationale or len(tool.rationale.strip()) < 5:
            issues.append(LintIssue("tool-rationale", "warning",
                                   f"Tool \"{tool.name}\" has missing/weak rationale",
                                   field="intent.tools_allowed"))
    return issues


# --- Rule: duplicate-tool ---

def _check_duplicate_tools(intent: Intent) -> LintIssue | None:
    seen: dict[str, int] = {}
    for tool in intent.tools_allowed:
        name_lower = tool.name.lower()
        if name_lower in seen:
            return LintIssue("duplicate-tool", "error",
                            f"Duplicate tool: \"{tool.name}\" (seen {seen[name_lower]} times)",
                            field="intent.tools_allowed")
        seen[name_lower] = 1
    return None


# --- Rule: non-negotiable-severity ---

def _check_non_negotiable_severity(intent: Intent) -> list[LintIssue]:
    issues = []
    for i, nn in enumerate(intent.non_negotiables):
        if nn.severity not in ("hard", "soft"):
            issues.append(LintIssue("non-negotiable-severity", "error",
                                   f"Non-negotiable {i+1} has invalid severity: \"{nn.severity}\"",
                                   field=f"intent.non_negotiables[{i}]"))
    return issues


# --- Rule: missing-escalation ---

def _check_missing_escalation(intent: Intent) -> LintIssue | None:
    if not intent.escalation:
        return LintIssue("missing-escalation", "warning",
                        "No escalation path defined for agent failures",
                        field="intent.escalation")
    return None


# --- Rule: missing-failure-modes ---

def _check_missing_failure_modes(intent: Intent) -> LintIssue | None:
    if not intent.failure_modes:
        return LintIssue("missing-failure-modes", "warning",
                        "No failure modes documented. How can this agent fail?",
                        field="intent.failure_modes")
    return None


# --- Rule: missing-boundaries ---

def _check_missing_boundaries(intent: Intent) -> LintIssue | None:
    if not intent.boundaries:
        return LintIssue("missing-boundaries", "warning",
                        "No scope/boundaries defined. What is in/out of scope?",
                        field="intent.boundaries")
    return None


# --- Rule: missing-denied-tools ---

def _check_missing_denied_tools(intent: Intent) -> LintIssue | None:
    if not intent.tools_denied:
        return LintIssue("missing-denied-tools", "warning",
                        "No denied tools section. Consider explicit tool denials.",
                        field="intent.tools_denied")
    return None


# --- Rule: goal-without-success-criteria ---

def _check_goal_without_success_criteria(intent: Intent) -> list[LintIssue]:
    issues = []
    for i, goal in enumerate(intent.goals):
        if not goal.success_criteria:
            issues.append(LintIssue("goal-without-success-criteria", "warning",
                                   f"Goal {i+1} (\"{goal.description[:40]}...\") has no success criteria",
                                   field=f"intent.goals[{i}]"))
    return issues


# --- Rule: empty-description ---

def _check_empty_descriptions(intent: Intent) -> list[LintIssue]:
    issues = []
    # Check agent description for placeholder
    if RE_PLACEHOLDER.match(intent.agent_description):
        issues.append(LintIssue("empty-description", "warning",
                               "Agent description has placeholder text",
                               field="agent.description"))
    # Check tool rationales for placeholder
    for tool in intent.tools_allowed:
        if RE_PLACEHOLDER.match(tool.rationale):
            issues.append(LintIssue("empty-description", "warning",
                                   f"Tool \"{tool.name}\" rationale has placeholder text",
                                   field="intent.tools_allowed"))
    return issues


# --- Rule: tools-not-in-source ---

def _check_tools_not_in_source(intent: Intent, source_text: str | None) -> list[LintIssue]:
    if not source_text:
        return []
    issues = []
    source_lower = source_text.lower()
    for tool in intent.tools_allowed:
        if tool.name.lower() not in source_lower:
            issues.append(LintIssue("tools-not-in-source", "warning",
                                   f"Tool \"{tool.name}\" declared but not mentioned in source text",
                                   field="intent.tools_allowed"))
    return issues


# --- Rule: duplicate-goals ---

def _check_duplicate_goals(intent: Intent) -> list[LintIssue]:
    issues = []
    seen_normalized: dict[str, int] = {}  # normalized -> count
    for i, goal in enumerate(intent.goals):
        # Normalize: lowercase, strip punctuation, truncate to 60 chars
        normalized = re.sub(r"[^a-z0-9 ]", "", goal.description.lower())[:60].strip()
        if normalized in seen_normalized:
            issues.append(LintIssue("duplicate-goals", "warning",
                                   f"Goal {i+1} looks similar to goal {seen_normalized[normalized]+1}: \"{goal.description[:40]}\"",
                                   field=f"intent.goals[{i}]"))
        else:
            seen_normalized[normalized] = i
    return issues


# --- Registry ---

_RULES = [
    ("agent-description", _check_agent_description),
    ("goals-required", _check_goals_required),
    ("duplicate-tool", _check_duplicate_tools),
    ("missing-escalation", _check_missing_escalation),
    ("missing-failure-modes", _check_missing_failure_modes),
    ("missing-boundaries", _check_missing_boundaries),
    ("missing-denied-tools", _check_missing_denied_tools),
]

_LIST_RULES = [
    ("goal-description-length", _check_goal_description_length),
    ("constraint-enforceable", _check_constraint_enforceable),
    ("tool-rationale", _check_tool_rationale),
    ("goal-without-success-criteria", _check_goal_without_success_criteria),
    ("empty-description", _check_empty_descriptions),
    ("tools-not-in-source", _check_tools_not_in_source),
    ("duplicate-goals", _check_duplicate_goals),
    ("non-negotiable-severity", _check_non_negotiable_severity),
]


def lint_intent(
    intent: Intent,
    source_text: str | None = None,
    *,
    raw_content: str | None = None,
    disabled_rules: set[str] | None = None,
) -> LintResult:
    """Run all lint rules against an intent spec.

    Args:
        intent: The parsed Intent model.
        source_text: Optional source text for cross-reference rules.
        raw_content: Raw intent.yaml text for per-line ``# intentspec: disable=`` rules.
        disabled_rules: Additional rule names to skip.

    Returns:
        LintResult with all issues found.
    """
    result = LintResult()
    disabled = set(disabled_rules or ())
    if raw_content:
        disabled |= parse_disabled_rules(raw_content)

    for name, checker in _RULES:
        try:
            issue = checker(intent)
            if issue is not None:
                result.issues.append(issue)
        except Exception as e:
            result.issues.append(LintIssue(name, "error", f"Rule crashed: {e}"))

    for name, checker in _LIST_RULES:
        try:
            issues = checker(intent, source_text) if name == "tools-not-in-source" else checker(intent)
            if issues:
                result.issues.extend(issues)
        except Exception as e:
            result.issues.append(LintIssue(name, "error", f"Rule crashed: {e}"))

    if disabled:
        result.issues = [i for i in result.issues if i.rule.lower() not in disabled]

    return result
