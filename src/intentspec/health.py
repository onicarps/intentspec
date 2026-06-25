"""Health command — terminal dashboard for IntentSpec.

Shows coverage trend, stale intents, orphaned specs, and IDS distribution.
"""
from __future__ import annotations

import glob
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from intentspec.models.intent import IntentValidationError
from intentspec.score.ids import compute_ids, IdsResult
from intentspec.source_resolve import is_orphaned
from intentspec.spec.validate import validate_file


@dataclass
class HealthResult:
    """Result of a health check."""

    scanned: int = 0
    valid: int = 0
    invalid: int = 0
    stale: int = 0
    orphaned: int = 0
    avg_score: float = 0.0
    scores: list[float] = field(default_factory=list)
    stale_files: list[str] = field(default_factory=list)
    orphaned_files: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def score_distribution(self) -> dict[str, int]:
        """Bucket scores into ranges."""
        buckets = {"90-100": 0, "70-89": 0, "50-69": 0, "0-49": 0}
        for s in self.scores:
            if s >= 90:
                buckets["90-100"] += 1
            elif s >= 70:
                buckets["70-89"] += 1
            elif s >= 50:
                buckets["50-69"] += 1
            else:
                buckets["0-49"] += 1
        return buckets

    def to_dict(self) -> dict[str, Any]:
        return {
            "scanned": self.scanned,
            "valid": self.valid,
            "invalid": self.invalid,
            "stale": self.stale,
            "orphaned": self.orphaned,
            "avg_score": round(self.avg_score, 1),
            "score_distribution": self.score_distribution,
            "stale_files": self.stale_files,
            "orphaned_files": self.orphaned_files,
            "errors": self.errors,
        }

    def to_text(self) -> str:
        lines = []
        lines.append("IntentSpec Health Report")
        lines.append("=" * 40)
        lines.append(f"  Scanned:    {self.scanned} intent.yaml files")
        lines.append(f"  Valid:      {self.valid}")
        lines.append(f"  Invalid:    {self.invalid}")
        lines.append(f"  Stale:      {self.stale} (>30 days)")
        lines.append(f"  Orphaned:   {self.orphaned}")
        lines.append(f"  Avg Score:  {self.avg_score:.1f}/100")
        lines.append("")
        lines.append("Score Distribution:")
        dist = self.score_distribution
        for bucket, count in dist.items():
            bar = "█" * min(count, 40)
            lines.append(f"  {bucket:8s} {bar} ({count})")
        if self.stale_files:
            lines.append("")
            lines.append("Stale Intents (>30 days):")
            for f in self.stale_files[:10]:
                lines.append(f"  ⚠ {f}")
            if len(self.stale_files) > 10:
                lines.append(f"  ... and {len(self.stale_files) - 10} more")
        if self.orphaned_files:
            lines.append("")
            lines.append("Orphaned Specs (no matching source):")
            for f in self.orphaned_files[:10]:
                lines.append(f"  ⚠ {f}")
        if self.errors:
            lines.append("")
            lines.append("Errors:")
            for e in self.errors[:5]:
                lines.append(f"  ✗ {e}")
        return "\n".join(lines)


def _is_stale(path: Path, max_days: int = 30) -> bool:
    """Check if a file hasn't been modified in max_days."""
    try:
        mtime = path.stat().st_mtime
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(mtime, tz=timezone.utc)
        return age > timedelta(days=max_days)
    except OSError:
        return False


def run_health(path: str = ".", *, stale_days: int = 30) -> HealthResult:
    """Run health check on intent.yaml files.

    Args:
        path: Directory or file to scan.
        stale_days: Number of days before a spec is considered stale.

    Returns:
        HealthResult with all metrics.
    """
    result = HealthResult()
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
    scores: list[float] = []

    for f in files:
        try:
            intent, errors, warnings = validate_file(f)
            if errors:
                result.invalid += 1
                result.errors.append(f"{f}: {errors[0]}")
            else:
                result.valid += 1

            # Score
            ids = compute_ids(intent)
            scores.append(ids.score)

            # Stale check
            if _is_stale(f, stale_days):
                result.stale += 1
                result.stale_files.append(str(f))

            # Orphaned check
            if is_orphaned(f):
                result.orphaned += 1
                result.orphaned_files.append(str(f))

        except IntentValidationError as e:
            result.invalid += 1
            result.errors.append(f"{f}: {e.errors[0] if e.errors else str(e)}")
        except Exception as e:
            result.invalid += 1
            result.errors.append(f"{f}: {e}")

    result.scores = scores
    if scores:
        result.avg_score = sum(scores) / len(scores)

    return result
