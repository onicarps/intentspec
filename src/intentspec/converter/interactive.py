"""Interactive review flow for converter output.

Allows users to review and edit extracted intent before writing to disk.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from intentspec.converter.types import FieldSource, ParseResult
from intentspec.models.intent import Intent


def review_interactive(result: ParseResult) -> ParseResult:
    """Run interactive review of a ParseResult.

    For each top-level field group, renders the field with ANSI color based
    on confidence, and prompts the user to keep/edit/drop.

    Args:
        result: The ParseResult to review.

    Returns:
        A new ParseResult with user-applied edits.
    """
    click.echo()
    click.echo(click.style("Interactive Review", bold=True))
    click.echo(click.style("=" * 40, dim=True))
    click.echo()
    click.echo("Review each field. Options: [K]eep / [E]dit / [D]rop / [F]inish review")
    click.echo()

    intent = result.intent

    # Review agent name
    click.echo(click.style("Agent Name:", bold=True))
    intent.agent_name = _review_field("agent name", intent.agent_name, "agent.name")

    # Review agent description
    click.echo(click.style("Agent Description:", bold=True))
    intent.agent_description = _review_field("description", intent.agent_description, "agent.description")

    # Review goals
    if intent.goals:
        click.echo(click.style("Goals:", bold=True))
        new_goals = []
        for i, goal in enumerate(intent.goals):
            conf = result.confidences.get(f"intent.goals[{i}].description", 0.5)
            color = _confidence_color(conf)
            click.echo(f"  {i+1}. {color}{goal.description}{click.style('', reset=True)}")
            action = click.prompt("  Action", type=click.Choice(["k", "e", "d", "f"]), default="k", show_choices=False)
            if action == "f":
                new_goals.extend(intent.goals[i:])
                break
            elif action == "k":
                new_goals.append(goal)
            elif action == "e":
                new_desc = click.prompt("  New description", default=goal.description)
                new_goals.append(goal.__class__(description=new_desc, priority=goal.priority))
            # action == "d" → drop
        intent.goals = new_goals

    # Review constraints
    if intent.constraints:
        click.echo(click.style("Constraints:", bold=True))
        new_constraints = []
        for i, constraint in enumerate(intent.constraints):
            conf = result.confidences.get(f"intent.constraints[{i}].rule", 0.5)
            color = _confidence_color(conf)
            enforceable = "enforceable" if constraint.enforceable else "guideline"
            click.echo(f"  {i+1}. [{enforceable}] {color}{constraint.rule}{click.style('', reset=True)}")
            action = click.prompt("  Action", type=click.Choice(["k", "e", "d", "f"]), default="k", show_choices=False)
            if action == "f":
                new_constraints.extend(intent.constraints[i:])
                break
            elif action == "k":
                new_constraints.append(constraint)
            elif action == "e":
                new_rule = click.prompt("  New rule", default=constraint.rule)
                new_enf = click.prompt("  Enforceable?", type=click.Bool, default=constraint.enforceable)
                new_constraints.append(constraint.__class__(rule=new_rule, enforceable=new_enf))
        intent.constraints = new_constraints

    # Review non-negotiables
    if intent.non_negotiables:
        click.echo(click.style("Non-Negotiables:", bold=True))
        new_nns = []
        for i, nn in enumerate(intent.non_negotiables):
            conf = result.confidences.get(f"intent.non_negotiables[{i}].rule", 0.5)
            color = _confidence_color(conf)
            click.echo(f"  {i+1}. [{nn.severity}] {color}{nn.rule}{click.style('', reset=True)}")
            action = click.prompt("  Action", type=click.Choice(["k", "e", "d", "f"]), default="k", show_choices=False)
            if action == "f":
                new_nns.extend(intent.non_negotiables[i:])
                break
            elif action == "k":
                new_nns.append(nn)
            elif action == "e":
                new_rule = click.prompt("  New rule", default=nn.rule)
                new_sev = click.prompt("  Severity", type=click.Choice(["hard", "soft"]), default=nn.severity)
                new_nns.append(nn.__class__(rule=new_rule, severity=new_sev))
        intent.non_negotiables = new_nns

    click.echo()
    click.echo("Review complete.")

    return ParseResult(
        intent=intent,
        confidences=result.confidences,
        sources=result.sources,
        warnings=result.warnings + ["User-reviewed via interactive mode"],
        format=result.format,
    )


def _review_field(name: str, value: str, key: str) -> str:
    """Review a single field value. Returns the (possibly edited) value."""
    click.echo(f"  Current: {value}")
    action = click.prompt(f"  {name}", type=click.Choice(["k", "e", "f"]), default="k", show_choices=False)
    if action == "f":
        return value  # Will be handled by caller
    elif action == "e":
        return click.prompt(f"  New {name}", default=value)
    return value  # action == "k"


def _confidence_color(confidence: float) -> str:
    """Return ANSI color code based on confidence score."""
    if confidence >= 0.75:
        return click.style("", fg="green")
    elif confidence >= 0.40:
        return click.style("", fg="yellow")
    else:
        return click.style("", fg="red")
