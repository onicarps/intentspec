"""Opt-in LLM extraction for ambiguous sections.

Uses OpenRouter API to augment rule-based extraction for fields with low confidence.
Results are cached locally to avoid redundant API calls.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from intentspec.converter.types import ConverterError, FieldSource, ParseResult
from intentspec.models.intent import ToolPermission

_CACHE_DIR = Path.home() / ".cache" / "intentspec" / "llm"

# Model to use for extraction
_DEFAULT_MODEL = "openrouter/anthropic/claude-sonnet-4"

# Confidence cap for LLM-derived fields
_LLM_CONFIDENCE_CAP = 0.70


def augment(result: ParseResult, *, model: str | None = None) -> ParseResult:
    """Augment a ParseResult with LLM extraction for low-confidence fields.

    Only fills missing fields or augments fields with confidence < 0.75.
    Never overrides high-confidence rule-based fields.

    Args:
        result: The ParseResult to augment.
        model: Optional model override. Defaults to environment variable
            OPENROUTER_MODEL or the built-in default.

    Returns:
        A new ParseResult with LLM-augmented fields. If the LLM call fails,
        returns the original result with a warning appended.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        result.warnings.append("LLM extraction skipped: OPENROUTER_API_KEY not set")
        return result

    model = model or os.environ.get("OPENROUTER_MODEL", _DEFAULT_MODEL)

    # Check if there are any low-confidence fields to augment
    low_conf = {k: v for k, v in result.confidences.items() if v < 0.75}
    if not low_conf:
        return result  # Nothing to augment

    try:
        llm_data = _call_llm(result, model, api_key)
    except Exception as exc:
        result.warnings.append(f"LLM extraction unavailable: {exc}")
        return result

    # Apply LLM results for low-confidence fields only
    intent = result.intent
    for key, value in llm_data.items():
        if key in result.confidences and result.confidences[key] >= 0.75:
            continue  # Don't override high-confidence fields

        # Handle both single values and arrays
        if key == "intent.goals" and isinstance(value, list):
            for v in value:
                if isinstance(v, str) and v.strip():
                    intent.goals.append(_parse_goal(v))
                    idx = len(intent.goals) - 1
                    result.confidences[f"intent.goals[{idx}].description"] = _LLM_CONFIDENCE_CAP
                    result.sources[f"intent.goals[{idx}].description"] = FieldSource(
                        extractor="llm", snippet=v[:60]
                    )
        elif key == "intent.constraints" and isinstance(value, list):
            for v in value:
                if isinstance(v, str) and v.strip():
                    intent.constraints.append(_parse_constraint(v))
                    idx = len(intent.constraints) - 1
                    result.confidences[f"intent.constraints[{idx}].rule"] = _LLM_CONFIDENCE_CAP
                    result.sources[f"intent.constraints[{idx}].rule"] = FieldSource(
                        extractor="llm", snippet=v[:60]
                    )
        elif key == "intent.non_negotiables" and isinstance(value, list):
            for v in value:
                if isinstance(v, str) and v.strip():
                    intent.non_negotiables.append(_parse_non_negotiable(v))
                    idx = len(intent.non_negotiables) - 1
                    result.confidences[f"intent.non_negotiables[{idx}].rule"] = _LLM_CONFIDENCE_CAP
                    result.sources[f"intent.non_negotiables[{idx}].rule"] = FieldSource(
                        extractor="llm", snippet=v[:60]
                    )
        elif key == "intent.tools_allowed" and isinstance(value, list):
            for v in value:
                if isinstance(v, str) and v.strip():
                    intent.tools_allowed.append(
                        ToolPermission(name=v.strip(), rationale="llm extraction")
                    )
                    idx = len(intent.tools_allowed) - 1
                    result.confidences[f"intent.tools.allowed[{idx}].name"] = _LLM_CONFIDENCE_CAP
                    result.sources[f"intent.tools.allowed[{idx}].name"] = FieldSource(
                        extractor="llm", snippet=v[:60]
                    )

    result.warnings.append(f"LLM augmentation applied for {len(llm_data)} field(s)")
    return result


def _call_llm(result: ParseResult, model: str, api_key: str) -> dict[str, str]:
    """Call OpenRouter API to extract intent fields.

    Returns a dict of field_key → extracted_value.
    """

    # Build prompt from the source content
    source_text = ""
    if result.intent.source_path:
        try:
            source_text = Path(result.intent.source_path).read_text(encoding="utf-8-sig")
        except OSError:
            pass

    if not source_text:
        # Reconstruct from the intent
        source_text = result.intent.to_yaml()

    prompt = _build_extraction_prompt(source_text, result)

    # Check cache
    cache_key = hashlib.sha256(prompt.encode()).hexdigest()
    cache_file = _CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            return cached.get("data", {})
        except (json.JSONDecodeError, OSError):
            pass  # Cache miss, continue

    # Make API call
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an intent extraction assistant. Extract structured intent from agent specification files. Return JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 2000,
    }

    req = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as resp:
            response_data = json.loads(resp.read().decode())
    except (URLError, HTTPError, OSError, TimeoutError) as exc:
        raise ConverterError(f"LLM API call failed: {exc}") from exc

    # Parse response
    try:
        content = response_data["choices"][0]["message"]["content"]
        extracted = json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        raise ConverterError(f"Failed to parse LLM response: {exc}") from exc

    # Cache result
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"data": extracted, "timestamp": time.time()}))
    except OSError:
        pass  # Cache write failure is non-fatal

    return extracted


def _build_extraction_prompt(source_text: str, result: ParseResult) -> str:
    """Build the LLM extraction prompt."""
    return f"""Extract the following fields from this agent specification.
Return a JSON object with any fields you can identify. Only include fields you find evidence for.

Source:
```
{source_text[:3000]}
```

Already extracted (do not override high-confidence fields):
- agent.name: {result.intent.agent_name} (confidence: {result.confidences.get("agent.name", 0):.2f})
- agent.description: {result.intent.agent_description} (confidence: {result.confidences.get("agent.description", 0):.2f})

Extract these fields as JSON:
- "intent.goals": array of goal description strings
- "intent.constraints": array of constraint rule strings
- "intent.non_negotiables": array of non-negotiable rule strings
- "intent.tools_allowed": array of tool name strings

Return JSON only, no explanation."""


def _parse_goal(text: str) -> Any:
    from intentspec.models.intent import Goal
    return Goal(description=text[:200], priority="medium")


def _parse_constraint(text: str) -> Any:
    from intentspec.models.intent import Constraint
    hard = text.upper().startswith(("NEVER", "MUST NOT", "DO NOT", "MUST", "ALWAYS"))
    return Constraint(rule=text[:500], enforceable=hard)


def _parse_non_negotiable(text: str) -> Any:
    from intentspec.models.intent import NonNegotiable
    soft = text.lower().startswith(("prefer", "should", "may"))
    return NonNegotiable(rule=text[:500], severity="soft" if soft else "hard")
