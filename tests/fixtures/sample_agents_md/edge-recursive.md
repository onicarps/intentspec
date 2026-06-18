# Recursive Reference Agent

A short companion fixture that delegates most of its rules to a sibling AGENTS.md to exercise the recursive-reference walker.

See also: kubernetes.md

## Goals
- Demonstrate that the converter follows a single sibling reference and merges its fields.
- Keep the local file deliberately sparse so the merged output is dominated by the referenced sibling.

## Constraints
- MUST verify the sibling file is in the same fixture directory before following the reference.
- ALWAYS lower confidence by 0.10 for fields imported from a referenced file.

## Non-negotiables
- NEVER follow more than two levels of references in a single parse.

## Tools

| Tool | Why |
|------|-----|
| python3 | Reference interpreter for the recursive walker |
