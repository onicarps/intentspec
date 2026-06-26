"""Tests for coverage trend tracking."""

from __future__ import annotations

from pathlib import Path

from intentspec.coverage_trend import get_trend, record_coverage


def test_record_and_read_trend(tmp_path: Path) -> None:
    intent = tmp_path / "intent.yaml"
    intent.write_text("version: '1.0'\n", encoding="utf-8")
    cache_dir = tmp_path / ".intentspec" / "cache"

    record_coverage(intent, 72.5, cache_dir=cache_dir)
    record_coverage(intent, 80.0, cache_dir=cache_dir)

    points = get_trend(intent, cache_dir=cache_dir)
    assert len(points) == 2
    assert points[-1].coverage == 80.0