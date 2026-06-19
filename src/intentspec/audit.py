"""Compliance audit report generation for `intentspec audit-report`.

Renders a SOC 2 / EU AI Act style compliance document from an intent.yaml,
including an agent inventory, a full intent spec dump, the Intent Debt Score
(IDS) with its component breakdown, and a footer carrying a generation
timestamp plus a SHA-256 hash of the raw source file.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from intentspec.models.intent import Intent, IntentValidationError
from intentspec.score.ids import IdsResult, compute_ids
from intentspec.spec.validate import validate_file

_COMPLIANCE_PREAMBLE = (
    "This report documents the declared intent of an AI agent to support "
    "compliance evidence under frameworks such as SOC 2 (security, "
    "availability, and processing integrity controls) and the EU AI Act "
    "(transparency, risk management, and human-oversight obligations). It is "
    "generated from the agent's intent.yaml and reflects the agent's "
    "documented goals, constraints, tool permissions, and escalation paths."
)


def generate_audit(path: Path | str, output_format: str = "text") -> str:
    """Generate a compliance audit report for an intent.yaml file.

    Args:
        path: Path to the intent.yaml file to audit.
        output_format: One of ``"text"``, ``"json"``, or ``"yaml"``.

    Returns:
        The rendered report as a string.

    Raises:
        FileNotFoundError: If ``path`` does not exist or cannot be read.
        IntentValidationError: If the file parses as YAML but fails v1 schema
            validation.
    """
    path = Path(path)
    file_bytes = path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    timestamp = datetime.now(timezone.utc).isoformat()

    intent, schema_errors, _semantic_warnings = validate_file(path)
    if schema_errors:
        raise IntentValidationError(schema_errors)

    ids_result = compute_ids(intent)
    data = _build_data(intent, ids_result, file_hash, timestamp, path)

    if output_format == "json":
        return json.dumps(data, indent=2)
    if output_format == "yaml":
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
    return _render_text(intent, ids_result, data)


def _build_data(
    intent: Intent,
    ids_result: IdsResult,
    file_hash: str,
    timestamp: str,
    path: Path,
) -> dict[str, Any]:
    """Assemble the structured report payload shared by all output formats."""
    full = intent.to_dict()
    return {
        "report": "IntentSpec Compliance Report",
        "generated_at": timestamp,
        "source_file": str(path),
        "compliance_frameworks": ["SOC 2", "EU AI Act"],
        "preamble": _COMPLIANCE_PREAMBLE,
        "agent": {
            "name": intent.agent_name,
            "type": intent.agent_type,
            "description": intent.agent_description,
            "version": intent.version,
        },
        "intent": full.get("intent", {}),
        "metadata": {
            "owner": intent.metadata.owner,
            "status": intent.metadata.status,
            "created": intent.metadata.created,
            "updated": intent.metadata.updated,
            "review_cycle": intent.metadata.review_cycle,
            "tags": list(intent.metadata.tags),
        },
        "score": {
            "ids": ids_result.score,
            "breakdown": ids_result.breakdown,
        },
        "version_history": [],
        "sha256": file_hash,
    }


def _render_text(intent: Intent, ids_result: IdsResult, data: dict[str, Any]) -> str:
    """Render the markdown text report."""
    lines: list[str] = []
    lines.append("# IntentSpec Compliance Report")
    lines.append("")
    lines.append(_COMPLIANCE_PREAMBLE)
    lines.append("")

    lines.append("## Agent Inventory")
    lines.append("")
    lines.append("| Name | Type | Description | Version |")
    lines.append("| --- | --- | --- | --- |")
    lines.append(
        f"| {intent.agent_name} | {intent.agent_type} | "
        f"{intent.agent_description} | {intent.version} |"
    )
    lines.append("")

    lines.append("## Intent Specification")
    lines.append("")

    lines.append("### Goals")
    if intent.goals:
        for g in intent.goals:
            criteria = f" (success: {g.success_criteria})" if g.success_criteria else ""
            lines.append(f"- [{g.priority}] {g.description}{criteria}")
    else:
        lines.append("- _None declared._")
    lines.append("")

    lines.append("### Constraints")
    if intent.constraints:
        for c in intent.constraints:
            kind = "enforceable" if c.enforceable else "human-judged"
            lines.append(f"- ({kind}) {c.rule}")
    else:
        lines.append("- _None declared._")
    lines.append("")

    lines.append("### Non-Negotiables")
    if intent.non_negotiables:
        for nn in intent.non_negotiables:
            lines.append(f"- [{nn.severity}] {nn.rule}")
    else:
        lines.append("- _None declared._")
    lines.append("")

    lines.append("### Tools")
    lines.append("")
    lines.append("**Allowed:**")
    if intent.tools_allowed:
        for t in intent.tools_allowed:
            rationale = f" — {t.rationale}" if t.rationale else ""
            lines.append(f"- {t.name}{rationale}")
    else:
        lines.append("- _None declared._")
    lines.append("")
    lines.append("**Denied:**")
    if intent.tools_denied:
        for t in intent.tools_denied:
            rationale = f" — {t.rationale}" if t.rationale else ""
            lines.append(f"- {t.name}{rationale}")
    else:
        lines.append("- _None declared._")
    lines.append("")

    lines.append("### Boundaries")
    if intent.boundaries:
        for b in intent.boundaries:
            lines.append(f"- in scope: {b.scope}")
            lines.append(f"  out of scope: {b.out_of_scope}")
    else:
        lines.append("- _None declared._")
    lines.append("")

    lines.append("### Escalation")
    if intent.escalation:
        lines.append(f"- trigger: {intent.escalation.trigger}")
        if intent.escalation.method:
            lines.append(f"- method: {intent.escalation.method}")
    else:
        lines.append("- _None declared._")
    lines.append("")

    lines.append("### Failure Modes")
    if intent.failure_modes:
        for fm in intent.failure_modes:
            lines.append(f"- {fm.mode}")
            lines.append(f"  mitigation: {fm.mitigation}")
    else:
        lines.append("- _None declared._")
    lines.append("")

    lines.append("### Metadata")
    lines.append(f"- owner: {intent.metadata.owner or '_unset_'}")
    lines.append(f"- status: {intent.metadata.status}")
    lines.append(f"- review_cycle: {intent.metadata.review_cycle}")
    if intent.metadata.created:
        lines.append(f"- created: {intent.metadata.created}")
    if intent.metadata.updated:
        lines.append(f"- updated: {intent.metadata.updated}")
    lines.append("")

    lines.append("## Intent Debt Score")
    lines.append("")
    lines.append(f"IDS: ~{round(ids_result.score)} / 100 (estimate)")
    lines.append("")
    lines.append("| Component | Score |")
    lines.append("| --- | --- |")
    for comp, val in ids_result.breakdown.items():
        lines.append(f"| {comp} | {val:.2f} |")
    lines.append("")

    lines.append("## Version History")
    lines.append("")
    lines.append("_No prior versions recorded. Version tracking is a placeholder._")
    lines.append("")

    lines.append("---")
    lines.append(f"Generated: {data['generated_at']}")
    lines.append(f"SHA-256: {data['sha256']}")

    return "\n".join(lines)
