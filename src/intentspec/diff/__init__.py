"""Diff command for IntentSpec — compares intent.yaml files with git or cached versions.

Features:
- Git integration for diffing intent.yaml files
- Semantic diff using Intent model comparison
- Fallback to cached .intentspec/cache/ when git unavailable
- Handles: shallow clones, detached HEAD, empty repos, monorepos
- --source-commit flag: compare from specific commit
- --format text|json|yaml support
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import yaml

from intentspec.converter import parse as converter_parse
from intentspec.converter.types import ConverterError, ParseResult
from intentspec.models.intent import Intent


def _find_git_repo_root(path: str) -> str | None:
    """Find git repository root directory for a given path."""
    current = os.path.abspath(path)
    parent = os.path.dirname(current)
    while current != parent:
        if os.path.isdir(os.path.join(current, ".git")):
            return current
        current = parent
        parent = os.path.dirname(current)
    return None


def _get_file_at_commit(repo_path: str, file_path: str, commit: str) -> str | None:
    """Get file content from a specific git commit."""
    try:
        rel = os.path.relpath(file_path, repo_path)
        result = subprocess.run(
            ["git", "show", f"{commit}:{rel}"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    return None


def _get_cached_path(source_path: str) -> Path | None:
    """Get path to cached intent file."""
    cache_dir = Path.home() / ".intentspec" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(Path(source_path).resolve()).encode()).hexdigest()[:16]
    p = cache_dir / f"{key}.yaml"
    return p if p.exists() else None


def _load_intent_from_text(text: str) -> Intent | None:
    """Parse intent from YAML text."""
    try:
        data = yaml.safe_load(text)
        if data and isinstance(data, dict):
            return Intent.from_dict(data)
    except Exception:
        pass
    return None


def _semantic_diff(old: Intent, new: Intent) -> dict[str, list[str]]:
    """Calculate semantic differences between two intents."""
    def norm(s: str) -> str:
        return " ".join(s.lower().split())

    old_goals = {norm(g.description) for g in old.goals}
    new_goals = {norm(g.description) for g in new.goals}
    old_constraints = {norm(c.rule) for c in old.constraints}
    new_constraints = {norm(c.rule) for c in new.constraints}
    old_tools = {t.name.lower() for t in old.tools_allowed}
    new_tools = {t.name.lower() for t in new.tools_allowed}
    old_nn = {norm(n.rule) for n in old.non_negotiables}
    new_nn = {norm(n.rule) for n in new.non_negotiables}

    return {
        "goals_added": [g.description for g in new.goals if norm(g.description) not in old_goals],
        "goals_removed": [g.description for g in old.goals if norm(g.description) not in new_goals],
        "constraints_added": [c.rule for c in new.constraints if norm(c.rule) not in old_constraints],
        "constraints_removed": [c.rule for c in old.constraints if norm(c.rule) not in new_constraints],
        "tools_added": sorted(new_tools - old_tools),
        "tools_removed": sorted(old_tools - new_tools),
        "non_negotiables_added": [n.rule for n in new.non_negotiables if norm(n.rule) not in old_nn],
        "non_negotiables_removed": [n.rule for n in old.non_negotiables if norm(n.rule) not in new_nn],
    }


def _format_diff(diff: dict[str, list[str]], fmt: str) -> str:
    """Format diff output."""
    has_changes = any(v for v in diff.values())
    if not has_changes:
        return "No changes detected."

    if fmt == "json":
        return json.dumps(diff, indent=2)
    if fmt == "yaml":
        return yaml.dump(diff, default_flow_style=False)

    lines = ["Semantic Differences:"]
    for key, items in diff.items():
        if items:
            label = key.replace("_", " ").title()
            lines.append(f"  {label}:")
            for item in items:
                prefix = "+" if "added" in key else "-"
                lines.append(f"    {prefix} {item}")
    return "\n".join(lines)


def run_diff(
    source: str,
    *,
    source_commit: str | None = None,
    semantic: bool = False,
    fmt: str = "text",
) -> str:
    """Run diff analysis and return formatted output.

    Args:
        source: Path to the intent.yaml or source spec file.
        source_commit: Git commit to compare from.
        semantic: Whether to use semantic diffing.
        fmt: Output format (text, json, yaml).

    Returns:
        Formatted diff string.
    """
    src_path = Path(source)
    if not src_path.exists():
        raise FileNotFoundError(f"Source not found: {source}")

    # Parse current intent
    try:
        current: ParseResult = converter_parse(src_path)
    except ConverterError as e:
        raise RuntimeError(f"Failed to parse source: {e}") from e

    old_intent: Intent | None = None

    # Try git-based diff first
    repo_root = _find_git_repo_root(source)
    if repo_root:
        if source_commit:
            content = _get_file_at_commit(repo_root, str(src_path.resolve()), source_commit)
            if content:
                old_intent = _load_intent_from_text(content)
        else:
            # Try to get the last committed version
            try:
                rel = os.path.relpath(str(src_path.resolve()), repo_root)
                result = subprocess.run(
                    ["git", "show", f"HEAD:{rel}"],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if result.returncode == 0:
                    old_intent = _load_intent_from_text(result.stdout)
            except (subprocess.SubprocessError, FileNotFoundError, OSError):
                pass

    # Fallback to cache
    if old_intent is None:
        cached = _get_cached_path(source)
        if cached:
            try:
                old_intent = _load_intent_from_text(cached.read_text(encoding="utf-8"))
            except Exception:
                pass

    if old_intent is None:
        return "No previous version found for comparison. Run `intentspec init` first to create a baseline."

    if semantic:
        diff = _semantic_diff(old_intent, current.intent)
        return _format_diff(diff, fmt)

    # Text-based diff
    old_yaml = old_intent.to_yaml()
    new_yaml = current.intent.to_yaml()

    if fmt == "json":
        return json.dumps({"old": old_yaml, "new": new_yaml}, indent=2)
    if fmt == "yaml":
        return yaml.dump({"old": old_yaml, "new": new_yaml}, default_flow_style=False)

    old_lines = old_yaml.splitlines()
    new_lines = new_yaml.splitlines()
    diff_lines = list(difflib.unified_diff(old_lines, new_lines, lineterm="", fromfile="old", tofile="new"))
    return "\n".join(diff_lines) if diff_lines else "No changes detected."


# Need difflib for text diff
import difflib  # noqa: E402
