"""Drift detection — compare intent.yaml against git history for staleness."""
from __future__ import annotations

import glob
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class DriftResult:
    """Result of drift detection."""

    scanned: int = 0
    drifted: int = 0
    drifted_files: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned": self.scanned,
            "drifted": self.drifted,
            "drifted_files": self.drifted_files,
            "errors": self.errors,
        }

    def to_text(self) -> str:
        lines = []
        lines.append("IntentSpec Drift Report")
        lines.append("=" * 40)
        lines.append(f"  Scanned:  {self.scanned} intent.yaml files")
        lines.append(f"  Drifted:  {self.drifted}")
        if self.drifted_files:
            lines.append("")
            lines.append("Drifted Files:")
            for d in self.drifted_files:
                lines.append(
                    f"  ⚠ {d['path']} — last commit {d['days_ago']:.0f} days ago"
                )
        return "\n".join(lines)


def _get_last_commit_age_days(path: Path) -> float | None:
    """Get days since last git commit touching this file's directory."""
    try:
        result = subprocess.run(
            [
                "git", "log", "-1", "--format=%ct",
                "--", str(path.parent),
            ],
            capture_output=True, text=True, timeout=5,
            cwd=str(path.parent),
        )
        if result.returncode == 0 and result.stdout.strip():
            commit_ts = float(result.stdout.strip())
            now = datetime.now(timezone.utc).timestamp()
            return (now - commit_ts) / 86400
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        pass
    return None


def _get_source_file_age_days(path: Path) -> float | None:
    """Get days since source file (AGENTS.md etc.) was last modified."""
    parent = path.parent
    for pattern in ["AGENTS.md", "SKILL.md", "crewai.yaml", "langgraph.yaml",
                    "autogen-config.yaml", "openai-agents.yaml"]:
        src = parent / pattern
        if src.exists():
            try:
                mtime = src.stat().st_mtime
                now = datetime.now(timezone.utc).timestamp()
                return (now - mtime) / 86400
            except OSError:
                pass
    return None


def run_drift(path: str = ".", *, threshold_days: int = 30) -> DriftResult:
    """Detect drifted intent specs.

    A spec is considered drifted if:
    - No git commit in the spec's directory for > threshold_days, OR
    - Source file (AGENTS.md etc.) was modified but intent.yaml wasn't updated

    Args:
        path: Directory or file to scan.
        threshold_days: Days before considering a spec drifted.

    Returns:
        DriftResult with all findings.
    """
    result = DriftResult()
    target = Path(path)

    if target.is_file():
        files = [target]
    elif target.is_dir():
        pattern = str(target / "**/intent.yaml")
        files = [Path(f) for f in glob.glob(pattern, recursive=True)]
    else:
        result.errors.append(f"Path not found: {target}")
        return result

    result.scanned = len(files)

    for f in files:
        try:
            # Check git commit age
            commit_age = _get_last_commit_age_days(f)
            source_age = _get_source_file_age_days(f)

            drifted = False
            reason = ""

            if commit_age is not None and commit_age > threshold_days:
                drifted = True
                reason = f"no commit in {commit_age:.0f} days"

            if source_age is not None and commit_age is not None:
                if source_age < commit_age - 1:  # Source changed after last commit
                    drifted = True
                    reason = f"source modified {source_age:.0f}d ago, last commit {commit_age:.0f}d ago"

            if drifted:
                result.drifted += 1
                result.drifted_files.append({
                    "path": str(f),
                    "days_ago": commit_age or 0,
                    "reason": reason,
                })

        except Exception as e:
            result.errors.append(f"{f}: {e}")

    return result
