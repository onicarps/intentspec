"""Validation — schema + semantic checks for intent.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema

from intentspec.models.intent import Intent
from intentspec.spec.schema import INTENT_SCHEMA_V1


def validate_schema(data: dict[str, Any], source_path: Path | None = None) -> list[str]:
    """Validate intent.yaml data against JSON Schema. Returns list of error messages."""
    errors: list[str] = []
    validator = jsonschema.Draft7Validator(INTENT_SCHEMA_V1)

    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = _format_path(error.absolute_path)
        message = error.message

        # Add helpful suggestions for common mistakes
        suggestion = _get_suggestion(error)
        if suggestion:
            message += f" (hint: {suggestion})"

        if source_path:
            errors.append(f"{source_path}:{path}: {message}")
        else:
            errors.append(f"{path}: {message}")

    return errors


def validate_semantic(intent: Intent, source_path: Path | None = None) -> list[str]:
    """Run semantic validation beyond schema checks. Returns list of warning/error messages."""
    errors: list[str] = []
    prefix = f"{source_path}:" if source_path else ""

    # Check for empty goals list (warning)
    if not intent.goals:
        errors.append(f"{prefix}intent.goals: empty — consider documenting at least one goal")

    # Check for duplicate tool names in allowed
    allowed_names = [t.name.lower() for t in intent.tools_allowed]
    seen: set[str] = set()
    for name in allowed_names:
        if name in seen:
            errors.append(f"{prefix}intent.tools.allowed: duplicate tool name '{name}'")
        seen.add(name)

    # Check for duplicate tool names in denied
    denied_names = [t.name.lower() for t in intent.tools_denied]
    seen = set()
    for name in denied_names:
        if name in seen:
            errors.append(f"{prefix}intent.tools.denied: duplicate tool name '{name}'")
        seen.add(name)

    # Check for overlap between allowed and denied
    overlap = set(allowed_names) & set(denied_names)
    for name in overlap:
        errors.append(f"{prefix}intent.tools: '{name}' appears in both allowed and denied")

    # Check for duplicate constraint rules
    constraint_rules = [c.rule.lower().strip() for c in intent.constraints]
    seen = set()
    for rule in constraint_rules:
        if rule in seen:
            errors.append(f"{prefix}intent.constraints: duplicate rule (case-insensitive)")
        seen.add(rule)

    # Check for duplicate non-negotiable rules
    nn_rules = [nn.rule.lower().strip() for nn in intent.non_negotiables]
    seen = set()
    for rule in nn_rules:
        if rule in seen:
            errors.append(f"{prefix}intent.non_negotiables: duplicate rule (case-insensitive)")
        seen.add(rule)

    # Check for non-negotiables that duplicate constraints
    for nn_rule in nn_rules:
        for c_rule in constraint_rules:
            if nn_rule == c_rule:
                errors.append(f"{prefix}intent: rule appears in both constraints and non_negotiables")

    # Check for missing rationale on tools
    for t in intent.tools_allowed:
        if not t.rationale:
            errors.append(f"{prefix}intent.tools.allowed '{t.name}': missing rationale")
    for t in intent.tools_denied:
        if not t.rationale:
            errors.append(f"{prefix}intent.tools.denied '{t.name}': missing rationale")

    # Check for very short descriptions
    if intent.agent_description and len(intent.agent_description) < 10:
        errors.append(f"{prefix}agent.description: very short ({len(intent.agent_description)} chars) — consider a more descriptive summary")

    for i, g in enumerate(intent.goals):
        if len(g.description) < 10:
            errors.append(f"{prefix}intent.goals[{i}].description: very short ({len(g.description)} chars)")

    return errors


def validate_file(path: Path | str) -> tuple[Intent, list[str], list[str]]:
    """
    Full validation of an intent.yaml file.
    Returns (intent, schema_errors, semantic_warnings).
    Raises IntentValidationError if schema validation fails.
    """
    path = Path(path)
    intent = Intent.from_file(path)

    # Parse raw for schema validation
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    schema_errors = validate_schema(raw, source_path=path)
    semantic_warnings = validate_semantic(intent, source_path=path)

    return intent, schema_errors, semantic_warnings


def _format_path(path: list[str | int]) -> str:
    """Format a JSON Schema path for display."""
    if not path:
        return "<root>"
    parts: list[str] = []
    for p in path:
        if isinstance(p, int):
            parts[-1] = f"{parts[-1]}[{p}]"
        else:
            parts.append(str(p))
    return ".".join(parts)


def _get_suggestion(error: jsonschema.ValidationError) -> str:
    """Generate helpful suggestions for common validation errors."""
    # Typo detection for field names
    if error.validator == "additionalProperties":
        prop = error.message.split("'")[1] if "'" in error.message else ""
        if prop:
            # Check if it's a known typo
            typos = {
                "constriants": "constraints",
                "non-negotiables": "non_negotiables",
                "non_negotiables": "non_negotiables",
                "goal": "goals",
                "tool": "tools",
                "constraint": "constraints",
                "description": "description",
                "severity": "severity",
                "enforceable": "enforceable",
                "rationale": "rationale",
                "mitigation": "mitigation",
                "out_of_scope": "out_of_scope",
                "success_criteria": "success_criteria",
                "review_cycle": "review_cycle",
            }
            if prop in typos:
                return f"did you mean '{typos[prop]}'?"

    # Enum value suggestions
    if error.validator == "enum":
        allowed = error.schema.get("enum", [])
        if allowed:
            return f"allowed values: {', '.join(str(v) for v in allowed)}"

    # Missing required field
    if error.validator == "required":
        missing = error.message.split("'")[1] if "'" in error.message else ""
        if missing:
            return f"'{missing}' is required"

    return ""
