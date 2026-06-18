"""Core converter types: ParseResult, FieldSource, ConverterError."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from intentspec.models.intent import Intent


class ConverterError(Exception):
    """Raised when a converter cannot proceed (bad format, missing source, etc.)."""


@dataclass
class FieldSource:
    """Provenance for a single extracted field.

    Attributes:
        line: 1-based source line in the input file, or None when not applicable.
        snippet: Short verbatim slice from the source that triggered the extraction.
        extractor: One of "rule", "llm", "user", "default".
    """

    line: int | None = None
    snippet: str = ""
    extractor: str = "rule"

    def to_dict(self) -> dict[str, Any]:
        return {"line": self.line, "snippet": self.snippet, "extractor": self.extractor}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldSource:
        return cls(
            line=data.get("line"),
            snippet=data.get("snippet", ""),
            extractor=data.get("extractor", "rule"),
        )


@dataclass
class ParseResult:
    """The output of every converter parser.

    Attributes:
        intent: The W1 Intent model populated with extracted data.
        confidences: JSONPath-like keys ("agent.name", "intent.goals[0].description")
            mapped to confidence scores in [0.0, 1.0].
        sources: Same key space as confidences — provenance per field.
        warnings: Human-readable extraction warnings.
        format: One of "agents_md", "skill_md", "agentskills", "quickstart".
    """

    intent: Intent
    confidences: dict[str, float] = field(default_factory=dict)
    sources: dict[str, FieldSource] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    format: str = ""

    def average_confidence(self) -> float:
        if not self.confidences:
            return 0.0
        return sum(self.confidences.values()) / len(self.confidences)

    def low_confidence_keys(self, threshold: float = 0.40) -> list[str]:
        return sorted(k for k, v in self.confidences.items() if v < threshold)

    def to_serializable(self) -> dict[str, Any]:
        """Render the full ParseResult as a JSON/YAML-friendly dict."""
        return {
            "intent": self.intent.to_dict(),
            "confidences": {k: round(v, 2) for k, v in sorted(self.confidences.items())},
            "sources": {
                k: self.sources[k].to_dict() for k in sorted(self.sources.keys())
            },
            "warnings": list(self.warnings),
            "format": self.format,
        }
