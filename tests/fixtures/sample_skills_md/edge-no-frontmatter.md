# Skill Without Frontmatter

A markdown file shaped like a SKILL but missing the leading YAML frontmatter block. The SKILL.md parser must reject this file with a clear `frontmatter`-related error rather than silently producing a half-formed Intent.

## Overview
Documents the contract: when `--from skill_md` is forced on a file with no frontmatter, the converter exits 1 with a stderr message about the missing `name` field; otherwise auto-detection routes the file to the AGENTS.md parser instead.

## Instructions
- MUST raise a ConverterError when the leading `---` frontmatter block is absent.
- DO NOT silently fall back to AGENTS.md parsing when the format was forced via `--from skill_md`.
- ALWAYS surface the missing-frontmatter case before any body-level extraction begins.

## Notes
- Never write an `intent.yaml` from a SKILL.md missing the required `name` key.
