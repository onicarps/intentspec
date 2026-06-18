# Malformed Markdown Agent

This fixture intentionally breaks several markdown invariants so that the parser must tolerate them without raising a Python traceback.

## Goals
- Survive an unterminated fenced code block without losing the surrounding sections.
- Tolerate unbalanced list indentation and mixed CRLF/LF line endings.

```python
def stuck():
    return "this fence is never closed"

## Constraints
- MUST not crash on broken fences or stray backticks.
   - DO NOT swallow exceptions; convert them into structured warnings.
 - ALWAYS keep emitting the rest of the document after a parser hiccup.

## Tools

| Tool | Why
|------|----
| python3 | Reference interpreter for fault-tolerant parsing
| pytest  some narrative without a closing pipe

## Non-negotiables
- NEVER let a markdown parsing error escape as an unhandled exception.

## Junk section
####  Excessive heading depth that has no body
- bullet without a parent
   * mixed bullet markers in the same list
- another bullet
)|*&^%$#@! stray punctuation outside any list
