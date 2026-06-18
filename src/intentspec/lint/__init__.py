"""Lint command for IntentSpec — quality checks for intent.yaml files.

Quality checks (not a full linting engine):
- goal descriptions > 10 chars
- constraints have enforceable field
- tools have rationale
- non-negotiables have severity
- no duplicate tool names
- no empty goals list
- agent description present and > 10 chars
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from intentspec.models.intent import Intent


@dataclass
class LintIssue:
    """A single lint issue."""
    rule: str
    message: str
    severity: str = "warning"  # "error" or "warning"
    field: str = ""


@dataclass
class LintResult:
    """Result of linting an intent."""
    issues: list[LintIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def is_clean(self) -> bool:
        return len(self.issues) == 0

    def to_text(self) -> str:
        if self.is_clean:
            return "No issues found."
        lines = [f"{len(self.issues)} issue(s) found:"]
        for issue in self.issues:
            icon = "✗" if issue.severity == "error" else "⚠"
            field = f" ({issue.field})" if issue.field else ""
            lines.append(f"  {icon} [{issue.rule}]{field}: {issue.message}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clean": self.is_clean,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "issues": [
                {"rule": i.rule, "message": i.message, "severity": i.severity, "field": i.field}
                for i in self.issues
            ],
        }


def lint_intent(intent: Intent) -> LintResult:
    """Run quality checks on an intent.

    Args:
        intent: The Intent model to lint.

    Returns:
        LintResult with all found issues.
    """
    issues: list[LintIssue] = []

    # Check agent description
    if not intent.agent_description or len(intent.agent_description.strip()) <= 10:
        issues.append(LintIssue(
            rule="agent-description",
            message="Agent description should be more than 10 characters",
            severity="warning",
            field="agent.description",
        ))

    # Check goals
    if not intent.goals:
        issues.append(LintIssue(
            rule="goals-required",
            message="At least one goal should be defined",
            severity="warning",
            field="intent.goals",
        ))
    for i, goal in enumerate(intent.goals):
        if not goal.description or len(goal.description.strip()) <= 10:
            issues.append(LintIssue(
                rule="goal-description-length",
                message=f"Goal {i} description should be more than 10 characters",
                severity="warning",
                field=f"intent.goals[{i}].description",
            ))

    # Check constraints have enforceable field
    for i, constraint in enumerate(intent.constraints):
        if constraint.enforceable is None:
            issues.append(LintIssue(
                rule="constraint-enforceable",
                message=f"Constraint {i} should have enforceable field set",
                severity="warning",
                field=f"intent.constraints[{i}].enforceable",
            ))

    # Check tools have rationale
    seen_tool_names: set[str] = set()
    for i, tool in enumerate(intent.tools_allowed):
        if not tool.rationale or len(tool.rationale.strip()) < 3:
            issues.append(LintIssue(
                rule="tool-rationale",
                message=f"Tool '{tool.name}' should have a rationale",
                severity="warning",
                field=f"intent.tools.allowed[{i}].rationale",
            ))
        if tool.name.lower() in seen_tool_names:
            issues.append(LintIssue(
                rule="duplicate-tool",
                message=f"Duplicate tool name: '{tool.name}'",
                severity="error",
                field=f"intent.tools.allowed[{i}].name",
            ))
        seen_tool_names.add(tool.name.lower())

    # Check non-negotiables have severity
    for i, nn in enumerate(intent.non_negotiables):
        if not nn.severity:
            issues.append(LintIssue(
                rule="non-negotiable-severity",
                message=f"Non-negotiable {i} should have severity set",
                severity="warning",
                field=f"intent.non_negotiables[{i}].severity",
            ))

    return LintResult(issues=issues)
