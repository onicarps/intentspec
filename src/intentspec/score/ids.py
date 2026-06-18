"""Intent Debt Score (IDS) calculation.

IDS = 100 - weighted sum of coverage components.
0 = fully documented, 100 = no documentation.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from intentspec.models.intent import Intent

# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "tool_coverage": 0.25,
    "goal_coverage": 0.15,
    "constraint_cov": 0.10,
    "non_negot_cov": 0.15,
    "freshness": 0.10,
    "completeness": 0.15,
    "consistency": 0.10,
}

# Freshness half-life in days
_FRESHNESS_HALF_LIFE = 30


@dataclass
class IdsResult:
    """Result of IDS score computation."""
    score: float
    breakdown: dict[str, float]
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def to_json(self) -> str:
        return json.dumps({"score": self.score, "breakdown": self.breakdown}, indent=2)

    def to_yaml(self) -> str:
        return yaml.dump({"score": self.score, "breakdown": self.breakdown}, default_flow_style=False)


def compute_ids(
    intent: Intent,
    *,
    weights: dict[str, float] | None = None,
    reference_time: float | None = None,
) -> IdsResult:
    """Calculate Intent Debt Score (IDS) for an intent.

    Args:
        intent: The parsed Intent model.
        weights: Custom weights for IDS components. Must sum to ~1.0.
            Unknown keys raise ValueError.
        reference_time: Unix timestamp for freshness calculation. Defaults to now.

    Returns:
        IdsResult with score (0-100) and per-component breakdown.
    """
    weights = dict(weights) if weights is not None else dict(DEFAULT_WEIGHTS)

    # Validate weights
    unknown = set(weights) - set(DEFAULT_WEIGHTS)
    if unknown:
        raise ValueError(f"Unknown weight keys: {unknown}")

    reference_time = reference_time or time.time()

    # Coverage components (from intent model fields)
    tool_cov = _calc_tool_coverage(intent)
    goal_cov = _calc_goal_coverage(intent)
    constraint_cov = _calc_constraint_coverage(intent)
    non_neg_cov = _calc_non_negotiable_coverage(intent)

    # Freshness
    freshness = _calc_freshness(intent, reference_time)

    # Completeness
    completeness = _calc_completeness(intent)

    # Consistency
    consistency = _calc_consistency(intent)

    # Weighted sum (higher = better documentation)
    breakdown = {
        "tool_coverage": tool_cov,
        "goal_coverage": goal_cov,
        "constraint_cov": constraint_cov,
        "non_negot_cov": non_neg_cov,
        "freshness": freshness,
        "completeness": completeness,
        "consistency": consistency,
    }

    weighted_sum = sum(breakdown[k] * weights.get(k, 0) for k in breakdown)
    score = max(0.0, min(100.0, round(100.0 * weighted_sum, 2)))

    return IdsResult(score=score, breakdown=breakdown, weights=weights)


def to_json(result: IdsResult) -> str:
    return result.to_json()


def to_yaml(result: IdsResult) -> str:
    return result.to_yaml()


def _calc_tool_coverage(intent: Intent) -> float:
    """Tool coverage: fraction of allowed tools with rationale."""
    if not intent.tools_allowed:
        return 1.0
    with_rationale = sum(1 for t in intent.tools_allowed if t.rationale)
    return with_rationale / len(intent.tools_allowed)


def _calc_goal_coverage(intent: Intent) -> float:
    """Goal coverage: fraction of goals with non-empty description."""
    if not intent.goals:
        return 1.0
    with_desc = sum(1 for g in intent.goals if g.description and len(g.description.strip()) > 3)
    return with_desc / len(intent.goals)


def _calc_constraint_coverage(intent: Intent) -> float:
    """Constraint coverage: fraction of enforceable constraints."""
    if not intent.constraints:
        return 1.0
    enforceable = sum(1 for c in intent.constraints if c.enforceable)
    return enforceable / len(intent.constraints)


def _calc_non_negotiable_coverage(intent: Intent) -> float:
    """Non-negotiable coverage: fraction of hard-severity non-negotiables."""
    if not intent.non_negotiables:
        return 1.0
    hard = sum(1 for nn in intent.non_negotiables if nn.severity == "hard")
    return hard / len(intent.non_negotiables)


def _calc_freshness(intent: Intent, reference_time: float) -> float:
    """Freshness score (0-1) based on how recently the intent was updated."""
    if intent.metadata.updated:
        try:
            from datetime import datetime, timezone
            updated_str = intent.metadata.updated.replace("Z", "+00:00")
            updated = datetime.fromisoformat(updated_str)
            age_days = (reference_time - updated.timestamp()) / 86400
            return math.exp(-0.693 * age_days / _FRESHNESS_HALF_LIFE)
        except (ValueError, OSError, OverflowError):
            return 0.0
    return 0.0


def _calc_completeness(intent: Intent) -> float:
    """Completeness: fraction of optional fields that are populated."""
    fields = [
        bool(intent.agent_description and len(intent.agent_description.strip()) > 10),
        bool(intent.goals),
        bool(intent.constraints),
        bool(intent.non_negotiables),
        bool(intent.tools_allowed),
        bool(intent.boundaries),
        bool(intent.escalation),
        bool(intent.failure_modes),
    ]
    return sum(fields) / len(fields)


def _calc_consistency(intent: Intent) -> float:
    """Consistency: 1.0 if no overlap between allowed and denied tools."""
    allowed = {t.name.lower() for t in intent.tools_allowed}
    denied = {t.name.lower() for t in intent.tools_denied}
    overlap = allowed & denied
    if overlap:
        return 0.0
    return 1.0
