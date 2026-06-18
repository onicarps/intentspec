---
name: api-spec-auditor
description: "Audits OpenAPI specs against an organisation's REST guidelines and flags drift."
version: 1.4.0
tags:
  - api
  - governance
  - openapi
---

# API Spec Auditor

## Overview
Walks an OpenAPI 3 document, checks naming, status-code coverage, error schemas, and emits a structured report tied to the team's REST guidelines.

## Goals
- Flag every endpoint missing a 4xx error schema or a 5xx fallback.
- Surface naming-convention drift (kebab-case paths, camelCase JSON fields).
- Produce a deterministic markdown report that diffs cleanly across runs.

## Instructions
- MUST consume OpenAPI 3.0 and 3.1 documents without round-tripping through extra tooling.
- MUST emit a non-zero exit code when severity-error issues remain unresolved.
- ALWAYS resolve `$ref` chains before applying naming rules.
- Prefer suggested fixes over hard failures when the guideline allows it.
- DO NOT mutate the source document; produce a side-by-side report instead.

## Notes
- Under no circumstances ship breaking-change advice without a maintainer's review.
- Never include real authentication tokens in example payloads.
- Treat undocumented endpoints as severity-error rather than warning.

## Caveats
- The auditor is best-effort on vendor extensions (`x-*`) and skips them with an info note.
