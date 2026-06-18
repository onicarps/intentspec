---
name: changelog-writer
description: "Drafts release notes from merged PR titles and labels."
version: 0.3.1
tags: [docs, release-notes]
---

# Changelog Writer

## Overview
Reads the latest tagged commit range and drafts a CHANGELOG.md entry grouped by feature, fix, and chore.

## Instructions
- MUST group entries by `feat`, `fix`, `chore`, and `docs` headings.
- MUST link every entry to its underlying pull request.
- Prefer present tense and active voice.

## Notes
- Never include private repository URLs in the rendered changelog.
- Ask the user to confirm the version bump before writing the file.
