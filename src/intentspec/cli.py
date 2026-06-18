"""CLI entry point — Click commands for intentspec."""

from __future__ import annotations

import glob
import sys
from pathlib import Path

import click

from intentspec.models.intent import IntentValidationError
from intentspec.spec.validate import validate_file
from intentspec.spec.formatter import Formatter


@click.group()
@click.version_option(version="0.1.0", prog_name="intentspec")
def main():
    """IntentSpec — Coverage and enforcement layer for AI agent infrastructure.

    Test coverage for agent behavior. Works with any spec format.
    """
    pass


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--strict", is_flag=True, help="Fail on warnings too")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def validate(path: str, strict: bool, output_format: str):
    """Validate intent.yaml against schema.

    PATH is the directory or file to validate. Defaults to current directory.
    """
    if output_format == "text":
        fmt = Formatter()
    else:
        fmt = Formatter(use_color=False)

    target = Path(path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = str(target / "**/intent.yaml")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        if not files:
            click.echo(fmt.warning(f"No intent.yaml found in {target}"))
            sys.exit(0)
    else:
        click.echo(fmt.error(f"Path not found: {target}"))
        sys.exit(1)

    exit_code = 0
    for f in sorted(files):
        try:
            intent, schema_errors, semantic_warnings = validate_file(f)

            if output_format == "json":
                import json
                result = {
                    "file": str(f),
                    "valid": len(schema_errors) == 0 and (not strict or len(semantic_warnings) == 0),
                    "schema_errors": schema_errors,
                    "semantic_warnings": semantic_warnings,
                }
                click.echo(json.dumps(result, indent=2))
            elif output_format == "yaml":
                import yaml
                result = {
                    "file": str(f),
                    "valid": len(schema_errors) == 0 and (not strict or len(semantic_warnings) == 0),
                    "schema_errors": schema_errors,
                    "semantic_warnings": semantic_warnings,
                }
                click.echo(yaml.dump(result, default_flow_style=False))
            else:
                click.echo(fmt.format_validation_errors(f, schema_errors, semantic_warnings))

            if schema_errors:
                exit_code = 1
            elif strict and semantic_warnings:
                exit_code = 2

        except IntentValidationError as e:
            if output_format == "json":
                import json
                click.echo(json.dumps({"file": str(f), "valid": False, "errors": e.errors}))
            elif output_format == "yaml":
                import yaml
                click.echo(yaml.dump({"file": str(f), "valid": False, "errors": e.errors}))
            else:
                for err in e.errors:
                    click.echo(fmt.error(f"{f}: {err}"))
            exit_code = 1

    sys.exit(exit_code)


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--by-agent", is_flag=True, help="Show per-agent breakdown")
@click.option("--weights", type=str, default=None, help="Custom weighting as JSON")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def score(path: str, by_agent: bool, weights: str | None, output_format: str):
    """Calculate Intent Debt Score (IDS 0-100).

    PATH is the directory or file to score. Defaults to current directory.
    """
    click.echo("score: not yet implemented")


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def coverage(path: str, output_format: str):
    """Show intent coverage percentage.

    PATH is the directory or file to analyze. Defaults to current directory.
    """
    click.echo("coverage: not yet implemented")


@main.command()
@click.argument("source", type=click.Path(exists=True))
@click.option("--yes", "skip_interactive", is_flag=True, help="Skip interactive review")
@click.option("--interactive/--no-interactive", default=True, help="Interactive review")
def init(source: str, skip_interactive: bool, interactive: bool):
    """Initialize intent.yaml from an existing agent spec.

    SOURCE is the path to an AGENTS.md, SKILL.md, or other supported format.
    """
    click.echo(f"init: not yet implemented (source: {source})")


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--semantic", is_flag=True, help="Show intent-level changes")
@click.option("--source-commit", "from_commit", type=str, default=None, help="Compare from this commit")
def diff(path: str, semantic: bool, from_commit: str | None):
    """Show intent changes between commits.

    PATH is the directory or file to diff. Defaults to current directory.
    """
    click.echo("diff: not yet implemented")


@main.command()
@click.option("--min-coverage", type=int, default=0, help="Minimum coverage threshold")
@click.option("--strict", is_flag=True, help="Fail on warnings")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def ci(min_coverage: int, strict: bool, output_format: str):
    """CI/CD hook — validate and score intent specs.

    Returns exit code 0 (pass), 1 (validation error), 2 (warning), or 3 (below threshold).
    """
    click.echo("ci: not yet implemented")


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def audit_report(path: str, output_format: str):
    """Generate compliance audit report.

    PATH is the directory or file to audit. Defaults to current directory.
    """
    click.echo("audit-report: not yet implemented")


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
def lint(path: str):
    """Check intent quality (not a full linting engine).

    PATH is the directory or file to lint. Defaults to current directory.
    """
    click.echo("lint: not yet implemented")


if __name__ == "__main__":
    main()
