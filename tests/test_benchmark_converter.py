"""Converter accuracy benchmark.

Measures field-level precision/recall of the converter against ground-truth fixtures.
Fails CI if accuracy falls below threshold.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from intentspec.converter import parse
from intentspec.converter.types import ConverterError

_FIXTURES = Path(__file__).parent / "fixtures"
_THRESHOLD = 0.75

# Field weights for weighted accuracy
_FIELD_WEIGHTS = {
    "tools.allowed": 0.30,
    "non_negotiables": 0.20,
    "constraints": 0.20,
    "goals": 0.15,
    "boundaries": 0.10,
    "metadata.tags": 0.05,
}


def _load_expected(path: Path) -> dict[str, Any]:
    """Load expected YAML fixture."""
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _extract_field_values(intent_data: dict, field: str) -> set[str]:
    """Extract values for a field from intent data."""
    values = set()
    if field == "tools.allowed":
        for tool in intent_data.get("intent", {}).get("tools", {}).get("allowed", []):
            values.add(tool.get("name", "").lower().strip())
    elif field == "non_negotiables":
        for nn in intent_data.get("intent", {}).get("non_negotiables", []):
            values.add(nn.get("rule", "").lower().strip())
    elif field == "constraints":
        for c in intent_data.get("intent", {}).get("constraints", []):
            values.add(c.get("rule", "").lower().strip())
    elif field == "goals":
        for g in intent_data.get("intent", {}).get("goals", []):
            values.add(g.get("description", "").lower().strip())
    elif field == "boundaries":
        for b in intent_data.get("intent", {}).get("boundaries", []):
            values.add(b.get("scope", "").lower().strip())
    elif field == "metadata.tags":
        for tag in intent_data.get("metadata", {}).get("tags", []):
            values.add(str(tag).lower().strip())
    return {v for v in values if v}


def _f1_score(expected: set[str], actual: set[str]) -> float:
    """Calculate F1 score between expected and actual sets."""
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    tp = len(expected & actual)
    precision = tp / len(actual) if actual else 0
    recall = tp / len(expected) if expected else 0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _find_fixture_pairs() -> list[tuple[Path, Path]]:
    """Find all (input, expected.yaml) fixture pairs."""
    pairs = []
    for fixture_dir in ["sample_agents_md", "sample_skills_md", "sample_agentskills"]:
        base = _FIXTURES / fixture_dir
        if not base.exists():
            continue
        for item in sorted(base.iterdir()):
            if item.is_file() and item.suffix == ".md" and item.stem != "edge-no-frontmatter":
                expected = item.parent / f"{item.stem}.expected.yaml"
                if expected.exists():
                    pairs.append((item, expected))
            elif item.is_dir():
                skill_md = item / "SKILL.md"
                expected = item / "expected.yaml"
                if skill_md.exists() and expected.exists():
                    pairs.append((skill_md, expected))
    return pairs


@pytest.mark.parametrize("source_path,expected_path", _find_fixture_pairs())
def test_converter_accuracy(source_path: Path, expected_path: Path):
    """Test converter accuracy against ground-truth fixtures."""
    result = parse(source_path)
    actual_data = result.intent.to_dict()
    expected_data = _load_expected(expected_path)

    scores = {}
    for field, weight in _FIELD_WEIGHTS.items():
        expected_vals = _extract_field_values(expected_data, field)
        actual_vals = _extract_field_values(actual_data, field)
        f1 = _f1_score(expected_vals, actual_vals)
        scores[field] = f1

    # Calculate weighted average
    total_weight = sum(_FIELD_WEIGHTS.values())
    weighted_score = sum(scores[f] * _FIELD_WEIGHTS[f] for f in scores) / total_weight

    # Store scores for reporting
    test_name = f"{source_path.parent.name}/{source_path.stem}"

    # Don't fail individual tests — the aggregate test below handles that
    assert weighted_score >= 0.0, f"Score should be non-negative for {test_name}"


def test_converter_meets_accuracy_threshold():
    """Aggregate test: converter must meet 75% weighted accuracy across all fixtures."""
    # Run all fixture pairs first
    pairs = _find_fixture_pairs()
    assert len(pairs) > 0, "No fixture pairs found for benchmark"

    total_weighted = 0.0
    total_weight = 0.0
    per_file_scores = {}

    for source_path, expected_path in pairs:
        result = parse(source_path)
        actual_data = result.intent.to_dict()
        expected_data = _load_expected(expected_path)

        file_score = 0.0
        file_weight = 0.0
        for field, weight in _FIELD_WEIGHTS.items():
            expected_vals = _extract_field_values(expected_data, field)
            actual_vals = _extract_field_values(actual_data, field)
            f1 = _f1_score(expected_vals, actual_vals)
            file_score += f1 * weight
            file_weight += weight

        weighted = file_score / file_weight if file_weight > 0 else 0
        per_file_scores[f"{source_path.parent.name}/{source_path.stem}"] = weighted
        total_weighted += weighted
        total_weight += 1

    aggregate = total_weighted / total_weight if total_weight > 0 else 0

    # Write benchmark report
    report_path = Path(".intentspec/benchmark/last-run.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Converter Benchmark Report\n",
        f"Aggregate Score: {aggregate:.2%}\n",
        f"Threshold: {_THRESHOLD:.0%}\n",
        f"Status: {'PASS' if aggregate >= _THRESHOLD else 'FAIL'}\n",
        "\n## Per-File Scores\n",
    ]
    for name, score in sorted(per_file_scores.items()):
        status = "✓" if score >= _THRESHOLD else "✗"
        lines.append(f"- {status} {name}: {score:.2%}")
    report_path.write_text("\n".join(lines))

    assert aggregate >= _THRESHOLD, (
        f"Converter accuracy {aggregate:.2%} below {_THRESHOLD:.0%} threshold. "
        f"Per-file: {per_file_scores}"
    )
