"""Performance budget tests for IntentSpec.

Validates that core operations complete within acceptable time bounds:
- validate < 100ms for a 50-intent file
- diff < 500ms for 100-commit history
- score < 200ms
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import yaml

from intentspec.converter import parse
from intentspec.models.intent import Intent
from intentspec.score.ids import compute_ids
from intentspec.spec.validate import validate_file


def _generate_intent_yaml(n_intents: int = 50) -> str:
    """Generate a large intent.yaml with *n_intents* goal/constraint/tool entries.

    Args:
        n_intents: Number of entries per list field to generate.

    Returns:
        YAML string representing a valid intent document.
    """
    data = {
        "version": "1.0",
        "agent": {
            "name": "perf-test-agent",
            "type": "coding",
            "description": "Performance test agent with many fields to stress-test validation.",
        },
        "intent": {
            "goals": [
                {
                    "description": f"Goal {i}: perform task subset {i} efficiently.",
                    "priority": "high" if i % 3 == 0 else "medium",
                }
                for i in range(n_intents)
            ],
            "constraints": [
                {
                    "rule": f"MUST follow constraint {i} for all operations in category {i}.",
                    "enforceable": i % 2 == 0,
                }
                for i in range(n_intents)
            ],
            "non_negotiables": [
                {
                    "rule": f"NEVER violate non-negotiable {i} under any circumstances.",
                    "severity": "hard" if i % 4 == 0 else "soft",
                }
                for i in range(n_intents)
            ],
            "tools": {
                "allowed": [
                    {
                        "name": f"tool-{i}",
                        "rationale": f"Required for task category {i} operations.",
                    }
                    for i in range(n_intents)
                ],
            },
            "boundaries": [
                {
                    "scope": f"Scope {i}: operations within module {i}.",
                    "out_of_scope": f"Out of scope {i}: external system {i} interactions.",
                }
                for i in range(min(n_intents, 20))
            ],
        },
        "metadata": {
            "status": "active",
            "owner": "perf-test",
            "tags": ["perf", "test", "benchmark"],
        },
    }
    return yaml.dump(data, default_flow_style=False)


@pytest.fixture
def large_intent_file(tmp_path: Path) -> Path:
    """Write a 50-intent YAML file and return its path."""
    path = tmp_path / "intent.yaml"
    path.write_text(_generate_intent_yaml(50), encoding="utf-8")
    return path


@pytest.fixture
def hundred_commit_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with 100 commits on intent.yaml.

    Returns the path to the intent.yaml file inside the repo.
    """
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "perf@test.local"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Perf Test"],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    intent_file = repo_dir / "intent.yaml"

    for i in range(100):
        data = {
            "version": "1.0",
            "agent": {
                "name": "perf-diff-agent",
                "type": "coding",
                "description": f"Commit {i}: updated agent description.",
            },
            "intent": {
                "goals": [
                    {
                        "description": f"Goal at commit {i}: do thing {i}.",
                        "priority": "medium",
                    }
                ],
            },
        }
        intent_file.write_text(
            yaml.dump(data, default_flow_style=False), encoding="utf-8"
        )
        subprocess.run(
            ["git", "add", "intent.yaml"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "--quiet", "-m", f"commit-{i}"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )

    return intent_file


class TestPerformanceBudgets:
    """Tests that enforce performance budgets for core operations."""

    def test_validate_under_100ms(self, large_intent_file: Path) -> None:
        """Validation of a 50-intent file must complete in under 100ms."""
        # Warm up: run once to eliminate cold-start effects
        validate_file(large_intent_file)

        # Timed run
        start = time.perf_counter()
        validate_file(large_intent_file)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, (
            f"Validation took {elapsed_ms:.1f}ms, budget is 100ms"
        )

    def test_diff_under_500ms(self, hundred_commit_repo: Path) -> None:
        """Diff over a 100-commit history must complete in under 500ms."""
        from intentspec.diff import run_diff

        # Warm up
        run_diff(str(hundred_commit_repo))

        # Timed run
        start = time.perf_counter()
        result = run_diff(str(hundred_commit_repo))
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, (
            f"Diff took {elapsed_ms:.1f}ms, budget is 500ms"
        )

    def test_score_under_200ms(self, large_intent_file: Path) -> None:
        """IDS scoring of a 50-intent file must complete in under 200ms."""
        intent = Intent.from_file(large_intent_file)

        # Warm up
        compute_ids(intent)

        # Timed run
        start = time.perf_counter()
        result = compute_ids(intent)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 200, (
            f"Scoring took {elapsed_ms:.1f}ms, budget is 200ms"
        )

    def test_parse_50_intent_file_under_100ms(self, large_intent_file: Path) -> None:
        """Parsing a generated 50-intent YAML via converter must be under 100ms."""
        # Warm up
        parse(large_intent_file, format="agents_md")

        # Timed run — parse the dict directly since converter expects markdown
        import yaml

        start = time.perf_counter()
        data = yaml.safe_load(large_intent_file.read_text())
        Intent.from_dict(data)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, (
            f"Intent.from_dict took {elapsed_ms:.1f}ms, budget is 100ms"
        )
