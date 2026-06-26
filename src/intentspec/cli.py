"""CLI entry point — Click commands for intentspec."""

from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import click
import yaml
from click.core import ParameterSource

from intentspec.audit import generate_audit
from intentspec.ci import CiConfigError, load_ci_config, resolve_ci_settings, run_ci
from intentspec.drift import run_drift
from intentspec.enforce import enforce_mcp, run_enforce
from intentspec.health import run_health
from intentspec.migrate import migrate as migrate_fn

try:
    from intentspec.dashboard import serve as _serve_dashboard
    _HAS_DASHBOARD = True
except ImportError:
    _HAS_DASHBOARD = False
from intentspec.converter import parse as converter_parse, parse_quickstart
from intentspec.converter.emit import to_full_json, to_full_yaml, to_intent_yaml
from intentspec.converter.types import ConverterError, ParseResult
from intentspec.coverage import analyze_coverage
from intentspec.source_resolve import read_source_text, resolve_source_for_intent
from intentspec.diff import run_diff
from intentspec.lint import lint_intent
from intentspec.models.intent import IntentValidationError
from intentspec.score.ids import compute_ids
from intentspec.spec.formatter import Formatter
from intentspec.spec.validate import validate_file, validate_schema, validate_semantic
from intentspec.test_engine import run_intent_tests
from intentspec.test_schema import IntentTestSchemaError, parse_intent_test


@click.group()
@click.version_option(version="1.1.0", prog_name="intentspec")
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
    target = Path(path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = str(target / "**/intent.yaml")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        if not files:
            click.echo("No intent.yaml found")
            sys.exit(0)
    else:
        click.echo(f"Path not found: {target}", err=True)
        sys.exit(1)

    custom_weights = None
    if weights:
        try:
            custom_weights = json.loads(weights)
        except json.JSONDecodeError as e:
            click.echo(f"Invalid weights JSON: {e}", err=True)
            sys.exit(1)

    exit_code = 0
    for f in sorted(files):
        try:
            result = validate_file(f)
            intent = result[0]
            ids_result = compute_ids(intent, weights=custom_weights)

            if output_format == "json":
                click.echo(ids_result.to_json())
            elif output_format == "yaml":
                click.echo(ids_result.to_yaml())
            else:
                click.echo(f"\n{f}")
                click.echo(f"  IDS Score: {ids_result.score}/100")
                for comp, val in ids_result.breakdown.items():
                    click.echo(f"    {comp}: {val:.2f}")
                if ids_result.score < 50:
                    exit_code = 2

        except Exception as e:
            click.echo(f"{f}: error: {e}", err=True)
            exit_code = 1

    sys.exit(exit_code)


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def coverage(path: str, output_format: str):
    """Show intent coverage percentage.

    PATH is the directory or file to analyze. Defaults to current directory.
    """
    target = Path(path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = str(target / "**/intent.yaml")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        if not files:
            click.echo("No intent.yaml found")
            sys.exit(0)
    else:
        click.echo(f"Path not found: {target}", err=True)
        sys.exit(1)

    for f in sorted(files):
        try:
            result = validate_file(f)
            intent = result[0]
            source = resolve_source_for_intent(f)
            cov = analyze_coverage(
                intent,
                source_path=str(source) if source else None,
            )

            if output_format == "json":
                import json
                click.echo(json.dumps(cov.to_dict(), indent=2))
            elif output_format == "yaml":
                import yaml
                click.echo(yaml.dump(cov.to_dict(), default_flow_style=False))
            else:
                click.echo(f"\n{f}")
                click.echo(cov.to_text())

        except Exception as e:
            click.echo(f"{f}: error: {e}", err=True)
            sys.exit(1)


@main.command()
@click.argument("source", type=click.Path(), required=False, default=None)
@click.option(
    "--from",
    "from_format",
    type=click.Choice(["agents_md", "skill_md", "agentskills", "crewai", "langgraph", "autogen", "openai_agents"]),
    default=None,
    help="Force input format instead of auto-detecting.",
)
@click.option("--quickstart", is_flag=True, default=False, help="Run the 3-question wizard.")
@click.option(
    "--template",
    "template_name",
    type=str,
    default=None,
    help="Use a built-in template (coding-agent, research-agent, service-agent, data-pipeline, multi-agent-coordinator). Use 'list' to see available templates.",
)
@click.option("--use-llm", "use_llm", is_flag=True, default=False, help="Augment with OpenRouter LLM (opt-in).")
@click.option(
    "--output",
    "-o",
    "output",
    type=click.Path(),
    default="intent.yaml",
    show_default=True,
    help="Output path. '-' writes to stdout.",
)
@click.option(
    "--interactive/--no-interactive",
    "interactive",
    default=True,
    help="Run interactive review (default when stdout is a TTY).",
)
@click.option("--yes", "-y", "skip_interactive", is_flag=True, default=False, help="Skip interactive review.")
@click.option("--name", "agent_name_override", type=str, default=None, help="Override agent name (skips prompt).")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format for stdout / file (text emits intent.yaml; json/yaml emit the full ParseResult).",
)
@click.option("--strict", is_flag=True, default=False, help="Refuse to write if the W1 validator returns errors.")
@click.option("--force", is_flag=True, default=False, help="Overwrite an existing output file.")
def init(
    source: str | None,
    from_format: str | None,
    quickstart: bool,
    template_name: str | None,
    use_llm: bool,
    output: str,
    interactive: bool,
    skip_interactive: bool,
    agent_name_override: str | None,
    output_format: str,
    strict: bool,
    force: bool,
):
    """Initialize intent.yaml from an existing agent spec or template.

    SOURCE is the path to an AGENTS.md, SKILL.md, or an agentskills directory.
    """
    if template_name is not None:
        _run_template_init(template_name, output, force, strict, agent_name_override)
        return

    if quickstart:
        result = _run_quickstart_wizard()
        source_label = "quickstart"
        rendered = _render_output(result, source_label, output_format)

        schema_errors, semantic_warnings = _validate_in_memory(result)
        if strict and (schema_errors or semantic_warnings):
            for err in schema_errors:
                click.echo(f"validator error: {err}", err=True)
            click.echo("Refusing to write under --strict due to validator errors.", err=True)
            sys.exit(1)

        if output == "-":
            click.echo(rendered, nl=False)
            sys.exit(0)

        out_path = Path(output)
        if out_path.exists() and not force:
            click.echo(f"Error: output path already exists (use --force to overwrite): {out_path}", err=True)
            sys.exit(1)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        click.echo(f"Wrote {out_path}")
        sys.exit(0)

    if source is None:
        click.echo("Error: SOURCE is required (or use --quickstart).", err=True)
        sys.exit(1)

    src_path = Path(source)
    if not src_path.exists():
        click.echo(f"Error: source not found — no such file or directory: {src_path}", err=True)
        sys.exit(1)

    try:
        result = converter_parse(src_path, use_llm=use_llm, format=from_format)
    except ConverterError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Run interactive review if enabled and stdout is a TTY
    if interactive and not skip_interactive and sys.stdout.isatty():
        from intentspec.converter.interactive import review_interactive
        result = review_interactive(result)

    source_label = str(src_path)
    rendered = _render_output(result, source_label, output_format)

    schema_errors, semantic_warnings = _validate_in_memory(result)
    if strict and (schema_errors or semantic_warnings):
        for err in schema_errors:
            click.echo(f"validator error: {err}", err=True)
        for warn in semantic_warnings:
            click.echo(f"validator warning: {warn}", err=True)
        click.echo("Refusing to write under --strict due to validator errors.", err=True)
        sys.exit(1)
    if schema_errors:
        for err in schema_errors:
            click.echo(f"warning: {err}", err=True)

    for warn in result.warnings:
        click.echo(f"warning: {warn}", err=True)

    if output == "-":
        click.echo(rendered, nl=False)
        sys.exit(0)

    out_path = Path(output)
    if out_path.exists() and not force:
        click.echo(f"Error: output path already exists (use --force to overwrite): {out_path}", err=True)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    click.echo(f"Wrote {out_path}")
    sys.exit(0)


def _run_quickstart_wizard() -> ParseResult:
    """Run the 3-question quickstart wizard and return a ParseResult."""
    click.echo("IntentSpec Quickstart Wizard")
    click.echo("=" * 40)

    # Question 1: Agent name and description
    agent_name = click.prompt("What is the agent name? (kebab-case)", type=str).strip()
    agent_description = click.prompt("What does the agent do? (one sentence)", type=str).strip()

    # Question 2: Agent type
    agent_type = click.prompt(
        "Agent type",
        type=click.Choice(["coding", "research", "service", "data", "coordinator", "custom"]),
        default="custom",
    )

    # Question 3: Non-negotiables
    non_negotiables_str = click.prompt(
        "What must it never do? (comma-separated, or press Enter to skip)",
        default="",
        type=str,
    ).strip()

    # Question 4: Tools
    tools_str = click.prompt(
        "What tools does it use? (comma-separated, or press Enter to skip)",
        default="",
        type=str,
    ).strip()

    answers = {
        "agent_name": agent_name,
        "agent_type": agent_type,
        "agent_description": agent_description,
    }

    if non_negotiables_str:
        answers["non_negotiables"] = non_negotiables_str

    if tools_str:
        answers["tools"] = tools_str

    return parse_quickstart(answers)


def _run_template_init(
    template_name: str,
    output: str,
    force: bool,
    strict: bool,
    agent_name_override: str | None = None,
) -> None:
    """Handle --template flag: copy built-in template to output path."""
    if template_name == "list":
        _list_templates()
        sys.exit(0)

    # Check if it looks like a URL
    if template_name.startswith(("http://", "https://")):
        click.echo("Community templates coming soon. Use a built-in template name.")
        click.echo("Run 'intentspec init --template list' to see available templates.")
        sys.exit(1)

    templates_dir = Path(__file__).parent / "templates"
    template_path = templates_dir / f"{template_name}.yaml"
    if not template_path.exists():
        click.echo(f"Error: unknown template '{template_name}'.", err=True)
        click.echo("Run 'intentspec init --template list' to see available templates.", err=True)
        sys.exit(1)

    # Read template
    template_content = template_path.read_text(encoding="utf-8")
    data = yaml.safe_load(template_content)
    if not isinstance(data, dict):
        click.echo(f"Error: template '{template_name}' is not valid YAML.", err=True)
        sys.exit(1)

    # Prompt for agent name (or use override)
    if agent_name_override:
        agent_name = agent_name_override
    else:
        default_name = data.get("agent", {}).get("name", "my-agent")
        agent_name = click.prompt("Agent name (kebab-case)", default=default_name).strip()
        if not agent_name:
            agent_name = default_name

    # Replace agent name in template
    if "agent" in data:
        data["agent"]["name"] = agent_name

    # Write output
    out_path = Path(output)
    if out_path.exists() and not force:
        click.echo(f"Error: output path already exists (use --force to overwrite): {out_path}", err=True)
        sys.exit(1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    # Validate
    intent, errors, warnings = validate_file(out_path)
    if errors:
        click.echo(f"Wrote {out_path} (with validation warnings):", err=True)
        for err in errors:
            click.echo(f"  validation error: {err}", err=True)
        if strict:
            out_path.unlink()
            sys.exit(1)
        sys.exit(0)

    click.echo(f"Wrote {out_path}")
    sys.exit(0)


def _list_templates() -> None:
    """List available built-in templates."""
    # cli.py is at src/intentspec/cli.py, so templates is at src/intentspec/templates/
    templates_dir = Path(__file__).parent / "templates"
    if not templates_dir.exists():
        click.echo("No templates directory found.")
        return
    templates = sorted(templates_dir.glob("*.yaml"))
    if not templates:
        click.echo("No templates available.")
        return
    click.echo("Available templates:")
    for t in templates:
        data = yaml.safe_load(t.read_text(encoding="utf-8"))
        name = t.stem
        agent_name = data.get("agent", {}).get("name", "?") if isinstance(data, dict) else "?"
        agent_type = data.get("agent", {}).get("type", "?") if isinstance(data, dict) else "?"
        click.echo(f"  {name:30s} type={agent_type:15s} default_name={agent_name}")


def _render_output(result, source_label: str, output_format: str) -> str:
    if output_format == "json":
        return to_full_json(result, source_label)
    if output_format == "yaml":
        return to_full_yaml(result, source_label)
    return to_intent_yaml(result, source_label)


def _validate_in_memory(result) -> tuple[list[str], list[str]]:
    data = result.intent.to_dict()
    schema_errors = validate_schema(data)
    semantic_warnings = validate_semantic(result.intent)
    return schema_errors, semantic_warnings


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--semantic", is_flag=True, help="Show intent-level changes")
@click.option("--source-commit", "from_commit", type=str, default=None, help="Compare from this commit")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def diff(path: str, semantic: bool, from_commit: str | None, output_format: str):
    """Show intent changes between commits.

    PATH is the directory or file to diff. Defaults to current directory.
    """
    target = Path(path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = str(target / "**/intent.yaml")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        if not files:
            click.echo("No intent.yaml found")
            sys.exit(0)
    else:
        click.echo(f"Path not found: {target}", err=True)
        sys.exit(1)

    for f in sorted(files):
        try:
            output = run_diff(str(f), source_commit=from_commit, semantic=semantic, fmt=output_format)
            click.echo(f"\n{f}")
            click.echo(output)
        except FileNotFoundError as e:
            click.echo(f"{f}: {e}", err=True)
            sys.exit(1)
        except RuntimeError as e:
            click.echo(f"{f}: {e}", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"{f}: error: {e}", err=True)
            sys.exit(1)


@main.command()
@click.argument("paths", type=click.Path(), nargs=-1)
@click.option("--min-coverage", type=click.IntRange(0, 100), default=0, help="Minimum coverage threshold (0-100)")
@click.option("--strict", is_flag=True, default=False, help="Fail on warnings too")
@click.option("--config", "config_path", type=click.Path(), default=None, help="Path to a .intentspec.yaml config file")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
@click.pass_context
def ci(
    ctx: click.Context,
    paths: tuple[str, ...],
    min_coverage: int,
    strict: bool,
    config_path: str | None,
    output_format: str,
):
    """CI/CD hook — aggregate validate, lint, score, and coverage checks.

    PATHS are the files or directories to check (directories glob **/intent.yaml).
    Defaults to the current directory when none are given.

    Returns exit code 0 (pass), 1 (validation error), 2 (warning), or 3 (fatal:
    missing spec, coverage below threshold, or bad config).
    """
    targets = list(paths) if paths else ["."]

    def _passed(name: str) -> bool:
        return ctx.get_parameter_source(name) == ParameterSource.COMMANDLINE

    try:
        config = load_ci_config(config_path)
        settings = resolve_ci_settings(
            config,
            cli_min_coverage=min_coverage if _passed("min_coverage") else None,
            cli_strict=strict if _passed("strict") else None,
            cli_format=output_format if _passed("output_format") else None,
        )
    except CiConfigError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(3)

    result = run_ci(
        targets,
        min_coverage=settings.min_coverage,
        strict=settings.strict,
        output_format=settings.output_format,
    )

    if settings.output_format == "json":
        click.echo(result.to_json())
    elif settings.output_format == "yaml":
        click.echo(result.to_yaml())
    else:
        click.echo(result.to_text(use_color=sys.stdout.isatty()))

    sys.exit(result.exit_code)


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def audit_report(path: str, output_format: str):
    """Generate compliance audit report.

    PATH is the directory or file to audit. Defaults to current directory.
    """
    target = Path(path)
    if target.is_dir():
        pattern = str(target / "**/intent.yaml")
        matches = sorted(Path(f) for f in glob.glob(pattern, recursive=True))
        if not matches:
            click.echo(f"Error: no intent.yaml found in {target}", err=True)
            sys.exit(3)
        target = matches[0]

    try:
        rendered = generate_audit(target, output_format=output_format)
    except IntentValidationError as e:
        for err in e.errors:
            click.echo(f"validation error: {err}", err=True)
        sys.exit(1)
    except (FileNotFoundError, IsADirectoryError, OSError) as e:
        click.echo(f"Error: cannot read {target}: {e}", err=True)
        sys.exit(3)

    click.echo(rendered)
    sys.exit(0)


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def lint(path: str, output_format: str):
    """Check intent quality (not a full linting engine).

    PATH is the directory or file to lint. Defaults to current directory.
    """
    target = Path(path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = str(target / "**/intent.yaml")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        if not files:
            click.echo("No intent.yaml found")
            sys.exit(0)
    else:
        click.echo(f"Path not found: {target}", err=True)
        sys.exit(1)

    exit_code = 0
    for f in sorted(files):
        try:
            result = validate_file(f)
            intent = result[0]
            raw_content = f.read_text(encoding="utf-8-sig")
            lint_result = lint_intent(
                intent,
                read_source_text(f),
                raw_content=raw_content,
            )

            if output_format == "json":
                import json
                click.echo(json.dumps(lint_result.to_dict(), indent=2))
            elif output_format == "yaml":
                import yaml
                click.echo(yaml.dump(lint_result.to_dict(), default_flow_style=False))
            else:
                click.echo(f"\n{f}")
                click.echo(lint_result.to_text())

            if lint_result.errors:
                exit_code = 1
            elif lint_result.warnings:
                exit_code = 2

        except Exception as e:
            click.echo(f"{f}: error: {e}", err=True)
            exit_code = 1

    sys.exit(exit_code)


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--stale-days", type=int, default=30, help="Days before a spec is considered stale")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def health(path: str, stale_days: int, output_format: str):
    """Terminal dashboard — coverage trend, stale intents, IDS distribution.

    PATH is the directory or file to scan. Defaults to current directory.
    """
    result = run_health(path, stale_days=stale_days)

    if output_format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    elif output_format == "yaml":
        click.echo(yaml.dump(result.to_dict(), default_flow_style=False))
    else:
        click.echo(result.to_text())

    if result.errors or result.invalid > 0:
        sys.exit(1)
    if result.stale > 0 or result.orphaned > 0:
        sys.exit(2)
    sys.exit(0)


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--threshold-days", type=int, default=30, help="Days before a spec is considered drifted")
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def drift(path: str, threshold_days: int, output_format: str):
    """Detect stale intents — compare intent.yaml against git history.

    PATH is the directory or file to scan. Defaults to current directory.
    """
    result = run_drift(path, threshold_days=threshold_days)

    if output_format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    elif output_format == "yaml":
        click.echo(yaml.dump(result.to_dict(), default_flow_style=False))
    else:
        click.echo(result.to_text())

    sys.exit(1 if result.drifted else 0)


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", type=int, default=8080, help="Port to serve on")
def dashboard(path: str, host: str, port: int):
    """Serve the IntentSpec dashboard (FastAPI + Chart.js).

    PATH is the directory to scan. Defaults to current directory.

    Requires: pip install fastapi uvicorn
    """
    if not _HAS_DASHBOARD:
        click.echo(
            "Error: dashboard requires FastAPI and uvicorn.\n"
            "Install with: pip install fastapi uvicorn",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Starting IntentSpec dashboard at http://{host}:{port}")
    click.echo(f"Scanning: {Path(path).resolve()}")
    click.echo("Press Ctrl+C to stop")
    _serve_dashboard(path, host=host, port=port)


@main.command()
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def migrate(path: str, output_format: str):
    """Migrate intent.yaml to latest schema version (additive, non-breaking).

    PATH is the directory or file to migrate. Defaults to current directory.
    """
    target = Path(path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = str(target / "**/intent.yaml")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        if not files:
            click.echo("No intent.yaml found")
            sys.exit(0)
    else:
        click.echo(f"Path not found: {target}", err=True)
        sys.exit(3)

    exit_code = 0
    for f in sorted(files):
        try:
            content = f.read_text(encoding="utf-8-sig")
            migrated = migrate_fn(content)

            if output_format == "json":
                click.echo(json.dumps({"file": str(f), "migrated": migrated}, indent=2))
            elif output_format == "yaml":
                click.echo(f"--- {f} ---")
                click.echo(migrated)
            else:
                click.echo(f"--- {f} ---")
                click.echo(migrated)

        except ValueError as e:
            click.echo(f"{f}: error: {e}", err=True)
            exit_code = 1

    sys.exit(exit_code)


@main.command("enforce")
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option(
    "--mcp",
    "--mcp-config",
    "mcp_config",
    type=click.Path(),
    default=None,
    help="Path to MCP server config JSON",
)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def enforce(path: str, mcp_config: str | None, output_format: str):
    """Enforce MCP tool capabilities against intent spec (intent-first).

    Validates that MCP server tools match what the agent SHOULD do
    (declared in intent spec), not just what it CAN do.

    PATH is the directory or file to enforce. Defaults to current directory.
    """
    target = Path(path)
    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = str(target / "**/intent.yaml")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
        if not files:
            click.echo("No intent.yaml found")
            sys.exit(0)
    else:
        click.echo(f"Path not found: {target}", err=True)
        sys.exit(3)

    exit_code = 0
    for f in sorted(files):
        try:
            result = validate_file(f)
            intent = result[0]

            allowed = [t.name for t in intent.tools_allowed] if intent.tools_allowed else []
            denied = [t.name for t in intent.tools_denied] if intent.tools_denied else []
            if mcp_config:
                enf_result = run_enforce(
                    config_path=mcp_config,
                    allowed_tools=allowed,
                    denied_tools=denied,
                )
            else:
                # Use intent's own tools as both allowed and server tools (self-check)
                enf_result = enforce_mcp(
                    intent_allowed_tools=allowed,
                    intent_denied_tools=denied,
                    server_tools=[],
                )

            if output_format == "json":
                click.echo(json.dumps({"file": str(f), **enf_result.to_dict()}, indent=2))
            elif output_format == "yaml":
                click.echo(yaml.dump({"file": str(f), **enf_result.to_dict()}, default_flow_style=False))
            else:
                click.echo(f"\n{f}")
                click.echo(enf_result.to_text())

            if enf_result.risks:
                exit_code = 2

        except Exception as e:
            click.echo(f"{f}: error: {e}", err=True)
            exit_code = 1

    sys.exit(exit_code)


@main.command("test")
@click.argument("path", type=click.Path(), default=".", required=False)
@click.option("--format", "output_format", type=click.Choice(["text", "json", "yaml"]), default="text")
def test(path: str, output_format: str):
    """Run structural intent tests (intent-test.yaml) against intent.yaml.

    PATH is the intent.yaml file or a directory containing it. Defaults to the
    current directory. The sibling intent-test.yaml (if present) is executed.

    Exit codes: 0 all pass (or no test file), 1 any error-severity failure,
    2 warning-severity-only failure, 3 missing intent.yaml or a fatal test-file
    schema error.
    """
    target = Path(path)
    if target.is_dir():
        intent_path = target / "intent.yaml"
    else:
        intent_path = target

    if not intent_path.is_file():
        click.echo(f"Error: no intent.yaml found at {target}", err=True)
        sys.exit(3)

    test_path = intent_path.parent / "intent-test.yaml"
    if not test_path.is_file():
        click.echo(f"No intent-test.yaml found next to {intent_path}; nothing to test.")
        sys.exit(0)

    try:
        intent, _schema_errors, _semantic_warnings = validate_file(intent_path)
    except IntentValidationError as e:
        for err in e.errors:
            click.echo(f"Error: {intent_path}: {err}", err=True)
        sys.exit(3)

    try:
        intent_test = parse_intent_test(test_path)
    except IntentTestSchemaError as e:
        click.echo(f"Error: invalid intent-test.yaml ({test_path}):", err=True)
        for err in e.errors:
            click.echo(f"  - {err}", err=True)
        sys.exit(3)

    suite = run_intent_tests(intent, intent_test)

    if output_format == "json":
        click.echo(json.dumps(suite.to_dict(), indent=2))
    elif output_format == "yaml":
        click.echo(yaml.dump(suite.to_dict(), default_flow_style=False, sort_keys=False))
    else:
        click.echo(f"\n{intent_path}")
        click.echo(suite.to_text())

    if suite.failed > 0 or suite.errors > 0:
        sys.exit(1)
    if suite.warnings > 0:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
