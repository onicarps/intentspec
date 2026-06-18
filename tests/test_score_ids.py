"""Unit tests for the IDS scoring engine."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from intentspec.models.intent import (
    Constraint,
    Goal,
    Intent,
    NonNegotiable,
    ToolPermission,
)
from intentspec.score.ids import (
    DEFAULT_WEIGHTS,
    IdsResult,
    compute_ids,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _make_intent(**kwargs) -> Intent:
    return Intent(
        agent_name=kwargs.get("agent_name", "test-agent"),
        agent_type=kwargs.get("agent_type", "custom"),
        agent_description=kwargs.get("agent_description", "A test agent"),
        goals=kwargs.get("goals", []),
        constraints=kwargs.get("constraints", []),
        non_negotiables=kwargs.get("non_negotiables", []),
        tools_allowed=kwargs.get("tools_allowed", []),
        tools_denied=kwargs.get("tools_denied", []),
        boundaries=kwargs.get("boundaries", []),
        escalation=kwargs.get("escalation", None),
        failure_modes=kwargs.get("failure_modes", []),
    )


def test_default_weights_match_architecture():
    assert DEFAULT_WEIGHTS == {
        "tool_coverage": 0.25,
        "goal_coverage": 0.15,
        "constraint_cov": 0.10,
        "non_negot_cov": 0.15,
        "freshness": 0.10,
        "completeness": 0.15,
        "consistency": 0.10,
    }
    assert math.isclose(sum(DEFAULT_WEIGHTS.values()), 1.0, abs_tol=1e-9)


def test_compute_ids_returns_result_with_breakdown_keys():
    intent = _make_intent(tools_allowed=[ToolPermission(name="git", rationale="vcs")])
    result = compute_ids(intent)
    assert isinstance(result, IdsResult)
    assert 0.0 <= result.score <= 100.0
    assert set(result.breakdown.keys()) == set(DEFAULT_WEIGHTS.keys())
    for v in result.breakdown.values():
        assert 0.0 <= v <= 1.0


def test_constraint_cov_with_no_constraints_is_one():
    intent = _make_intent()
    result = compute_ids(intent)
    assert result.breakdown["constraint_cov"] == 1.0
    assert result.breakdown["non_negot_cov"] == 1.0


def test_constraint_cov_ratio():
    intent = _make_intent(
        constraints=[
            Constraint(rule="A", enforceable=True),
            Constraint(rule="B", enforceable=False),
            Constraint(rule="C", enforceable=True),
            Constraint(rule="D", enforceable=False),
        ],
    )
    result = compute_ids(intent)
    assert result.breakdown["constraint_cov"] == 0.5


def test_non_negot_cov_ratio():
    intent = _make_intent(
        non_negotiables=[
            NonNegotiable(rule="x", severity="hard"),
            NonNegotiable(rule="y", severity="soft"),
            NonNegotiable(rule="z", severity="hard"),
        ],
    )
    result = compute_ids(intent)
    assert math.isclose(result.breakdown["non_negot_cov"], 2 / 3, abs_tol=1e-9)


def test_consistency_zero_on_conflict():
    intent = _make_intent(
        tools_allowed=[ToolPermission(name="docker", rationale="r1")],
        tools_denied=[ToolPermission(name="docker", rationale="r2")],
    )
    result = compute_ids(intent)
    assert result.breakdown["consistency"] == 0.0


def test_consistency_one_when_no_conflict():
    intent = _make_intent(
        tools_allowed=[ToolPermission(name="git", rationale="vcs")],
        tools_denied=[ToolPermission(name="rm", rationale="dangerous")],
    )
    result = compute_ids(intent)
    assert result.breakdown["consistency"] == 1.0


def test_freshness_decays_to_half_at_30_days():
    intent = _make_intent()
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    intent.metadata.updated = thirty_days_ago.isoformat()
    result = compute_ids(intent)
    assert math.isclose(result.breakdown["freshness"], 0.5, abs_tol=0.02)


def test_freshness_zero_when_no_updated():
    intent = _make_intent()
    intent.metadata.updated = ""
    result = compute_ids(intent)
    assert result.breakdown["freshness"] == 0.0


def test_freshness_zero_for_unparseable_date():
    intent = _make_intent()
    intent.metadata.updated = "not-a-date"
    result = compute_ids(intent)
    assert result.breakdown["freshness"] == 0.0


def test_completeness_full_when_all_optional_fields_populated():
    from intentspec.models.intent import (
        Boundary,
        Escalation,
        FailureMode,
    )
    intent = _make_intent(
        goals=[Goal(description="g")],
        constraints=[Constraint(rule="r", enforceable=True)],
        non_negotiables=[NonNegotiable(rule="n", severity="hard")],
        tools_allowed=[ToolPermission(name="git", rationale="r")],
        boundaries=[Boundary(scope="s", out_of_scope="o")],
        escalation=Escalation(trigger="t", method="m"),
        failure_modes=[FailureMode(mode="x", mitigation="y")],
    )
    result = compute_ids(intent)
    assert math.isclose(result.breakdown["completeness"], 1.0, abs_tol=1e-9)


def test_completeness_zero_when_all_empty():
    intent = _make_intent(agent_description="")
    result = compute_ids(intent)
    assert result.breakdown["completeness"] == 0.0


def test_compute_ids_with_override_weights_only_tool_coverage():
    intent = _make_intent(tools_allowed=[ToolPermission(name="git", rationale="r")])
    weights = {
        "tool_coverage": 1.0,
        "goal_coverage": 0.0,
        "constraint_cov": 0.0,
        "non_negot_cov": 0.0,
        "freshness": 0.0,
        "completeness": 0.0,
        "consistency": 0.0,
    }
    result = compute_ids(intent, weights=weights)
    expected = 100.0 * result.breakdown["tool_coverage"]
    assert math.isclose(result.score, expected, abs_tol=0.5)


def test_compute_ids_score_formula_is_weighted_sum():
    intent = _make_intent(
        tools_allowed=[ToolPermission(name="git", rationale="r")],
        goals=[Goal(description="goal one")],
    )
    result = compute_ids(intent)
    expected = 100.0 * sum(DEFAULT_WEIGHTS[k] * result.breakdown[k] for k in DEFAULT_WEIGHTS)
    assert math.isclose(result.score, expected, abs_tol=0.5)


def test_compute_ids_end_to_end_on_valid_fixture():
    intent = Intent.from_file(FIXTURE_DIR / "valid_intent.yaml")
    result = compute_ids(intent)
    assert isinstance(result, IdsResult)
    assert 0 <= result.score <= 100
    assert set(result.breakdown.keys()) == set(DEFAULT_WEIGHTS.keys())


def test_unknown_weight_key_raises():
    intent = _make_intent()
    with pytest.raises(ValueError, match="weight"):
        compute_ids(intent, weights={"bogus_key": 1.0})


def test_to_json_emits_parseable_object():
    import json
    from intentspec.score.ids import to_json
    intent = _make_intent(tools_allowed=[ToolPermission(name="git", rationale="r")])
    result = compute_ids(intent)
    payload = to_json(result)
    parsed = json.loads(payload)
    assert "score" in parsed and "breakdown" in parsed
    assert set(parsed["breakdown"].keys()) == set(DEFAULT_WEIGHTS.keys())


def test_to_yaml_emits_parseable_document():
    import yaml
    from intentspec.score.ids import to_yaml
    intent = _make_intent(tools_allowed=[ToolPermission(name="git", rationale="r")])
    result = compute_ids(intent)
    payload = to_yaml(result)
    parsed = yaml.safe_load(payload)
    assert "score" in parsed and "breakdown" in parsed
    assert set(parsed["breakdown"].keys()) == set(DEFAULT_WEIGHTS.keys())


def test_score_computation_under_budget():
    import time
    intent = Intent.from_file(FIXTURE_DIR / "valid_intent.yaml")
    start = time.perf_counter()
    compute_ids(intent)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 600, f"compute_ids took {elapsed_ms:.0f}ms"
