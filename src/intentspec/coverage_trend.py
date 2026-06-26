"""Coverage trend tracking for intent.yaml files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_CACHE_DIR = Path(".intentspec/cache")
HISTORY_FILENAME = "coverage-history.json"
MAX_ENTRIES = 50


@dataclass
class CoverageTrendPoint:
    """A single recorded coverage sample."""

    timestamp: str
    coverage: float
    file: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "coverage": self.coverage,
            "file": self.file,
        }


def _history_path(cache_dir: Path | None = None) -> Path:
    base = cache_dir or DEFAULT_CACHE_DIR
    return base / HISTORY_FILENAME


def _load_history(cache_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    path = _history_path(cache_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_history(history: dict[str, list[dict[str, Any]]], cache_dir: Path | None = None) -> None:
    path = _history_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")


def record_coverage(
    intent_path: Path | str,
    coverage: float,
    *,
    cache_dir: Path | None = None,
) -> CoverageTrendPoint:
    """Append a coverage sample for ``intent_path``."""
    key = str(Path(intent_path).resolve())
    history = _load_history(cache_dir)
    point = CoverageTrendPoint(
        timestamp=datetime.now(timezone.utc).isoformat(),
        coverage=round(coverage, 2),
        file=key,
    )
    entries = history.setdefault(key, [])
    entries.append(point.to_dict())
    history[key] = entries[-MAX_ENTRIES:]
    _save_history(history, cache_dir)
    return point


def get_trend(intent_path: Path | str, *, cache_dir: Path | None = None) -> list[CoverageTrendPoint]:
    """Return recorded coverage samples for ``intent_path``."""
    key = str(Path(intent_path).resolve())
    history = _load_history(cache_dir)
    return [
        CoverageTrendPoint(
            timestamp=item["timestamp"],
            coverage=float(item["coverage"]),
            file=item.get("file", key),
        )
        for item in history.get(key, [])
        if isinstance(item, dict) and "timestamp" in item and "coverage" in item
    ]