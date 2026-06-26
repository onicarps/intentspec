"""Analyze agent specs for content marketing (Phase 2C).

Scans intent.yaml files and optional source specs to produce aggregate
statistics for blog posts and social content.
"""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from intentspec.converter import parse
from intentspec.models.intent import Intent
from intentspec.score.ids import compute_ids
from intentspec.spec.validate import validate_file


@dataclass
class SpecStats:
    """Aggregate statistics across analyzed specs."""

    label: str = "all"
    total: int = 0
    with_constraints: int = 0
    with_non_negotiables: int = 0
    with_denied_tools: int = 0
    with_escalation: int = 0
    with_failure_modes: int = 0
    avg_ids: float = 0.0
    ids_scores: list[float] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "total": self.total,
            "with_constraints": self.with_constraints,
            "with_non_negotiables": self.with_non_negotiables,
            "with_denied_tools": self.with_denied_tools,
            "with_escalation": self.with_escalation,
            "with_failure_modes": self.with_failure_modes,
            "avg_ids": round(self.avg_ids, 1),
            "pct_no_constraints": self._pct_missing(self.with_constraints),
            "pct_no_non_negotiables": self._pct_missing(self.with_non_negotiables),
            "pct_no_denied_tools": self._pct_missing(self.with_denied_tools),
            "pct_no_escalation": self._pct_missing(self.with_escalation),
            "sources": self.sources,
        }

    def _pct_missing(self, present: int) -> float:
        if self.total == 0:
            return 0.0
        return round(100 * (1 - present / self.total), 1)

    def to_markdown(self) -> str:
        d = self.to_dict()
        lines = [
            "# Agent Spec Analysis — Content Marketing Data",
            "",
            f"**Population:** {d['label']}",
            f"**Sample size:** {d['total']} agent specs",
            f"**Average IDS score:** ~{d['avg_ids']}/100",
            "",
            "## Key Findings",
            "",
            f"- **{d['pct_no_constraints']}%** have no constraints declared",
            f"- **{d['pct_no_non_negotiables']}%** have no non-negotiables (hard boundaries)",
            f"- **{d['pct_no_denied_tools']}%** have no denied tools (no explicit blocklist)",
            f"- **{d['pct_no_escalation']}%** have no escalation path defined",
            "",
            "## Headline Options",
            "",
            f'> "We analyzed {d["total"]} agent specs. {d["pct_no_non_negotiables"]:.0f}% have no hard boundaries."',
            "",
            f'> "{d["pct_no_denied_tools"]:.0f}% of agent specs never declare which tools are forbidden."',
            "",
            "## Sample Sources",
            "",
        ]
        for src in d["sources"][:20]:
            lines.append(f"- {src}")
        if len(d["sources"]) > 20:
            lines.append(f"- ... and {len(d['sources']) - 20} more")
        return "\n".join(lines)


def _record_intent(stats: SpecStats, intent: Intent, source: str) -> None:
    stats.total += 1
    stats.sources.append(source)
    if intent.constraints:
        stats.with_constraints += 1
    if intent.non_negotiables:
        stats.with_non_negotiables += 1
    if intent.tools_denied:
        stats.with_denied_tools += 1
    if intent.escalation and intent.escalation.trigger:
        stats.with_escalation += 1
    if intent.failure_modes:
        stats.with_failure_modes += 1
    stats.ids_scores.append(compute_ids(intent).score)


def _iter_declared_specs(root: Path) -> list[Path]:
    patterns = ["**/intent.yaml", "**/valid_intent.yaml", "**/templates/*.yaml"]
    found: list[Path] = []
    seen: set[str] = set()
    for pattern in patterns:
        for spec in glob.glob(str(root / pattern), recursive=True):
            if spec not in seen:
                seen.add(spec)
                found.append(Path(spec))
    return sorted(found)


def _analyze_intent_yaml(root: Path) -> SpecStats:
    stats = SpecStats(label="intent.yaml (declared specs)")
    for spec_path in _iter_declared_specs(root):
        try:
            intent, errors, _ = validate_file(spec_path)
            if errors:
                continue
            _record_intent(stats, intent, str(spec_path.relative_to(root)))
        except Exception:
            continue
    if stats.ids_scores:
        stats.avg_ids = sum(stats.ids_scores) / len(stats.ids_scores)
    return stats


def _analyze_converted_sources(root: Path) -> SpecStats:
    stats = SpecStats(label="converted from AGENTS.md / SKILL.md")
    patterns = ["**/*.md"]
    seen: set[str] = set()
    for src in sorted(glob.glob(str(root / "**/*.md"), recursive=True)):
        src_path = Path(src)
        if src_path.name == "intent.yaml":
            continue
        rel = str(src_path.relative_to(root))
        if rel in seen:
            continue
        seen.add(rel)
        try:
            result = parse(src_path)
            _record_intent(stats, result.intent, rel)
        except Exception:
            continue
    if stats.ids_scores:
        stats.avg_ids = sum(stats.ids_scores) / len(stats.ids_scores)
    return stats


def analyze_directory(path: str = ".") -> SpecStats:
    """Analyze all intent.yaml and convertible source specs under path."""
    root = Path(path)
    declared = _analyze_intent_yaml(root)
    converted = _analyze_converted_sources(root)

    combined = SpecStats(label="combined (declared + converted)")
    for part in (declared, converted):
        combined.total += part.total
        combined.with_constraints += part.with_constraints
        combined.with_non_negotiables += part.with_non_negotiables
        combined.with_denied_tools += part.with_denied_tools
        combined.with_escalation += part.with_escalation
        combined.with_failure_modes += part.with_failure_modes
        combined.ids_scores.extend(part.ids_scores)
        combined.sources.extend(part.sources)

    if combined.ids_scores:
        combined.avg_ids = sum(combined.ids_scores) / len(combined.ids_scores)

    return combined


def analyze_directory_report(path: str = ".") -> str:
    """Return markdown report with declared vs converted breakdown."""
    root = Path(path)
    declared = _analyze_intent_yaml(root)
    converted = _analyze_converted_sources(root)
    combined = analyze_directory(path)
    parts = [declared.to_markdown(), "", "---", "", converted.to_markdown(), "", "---", "", combined.to_markdown()]
    return "\n".join(parts)