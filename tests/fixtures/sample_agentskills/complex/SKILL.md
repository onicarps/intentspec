---
name: dataset-validator
description: "Validates analytics datasets against a published schema and emits a coverage report."
version: 2.0.0
tags:
  - data
  - validation
  - quality
---

# Dataset Validator

## Overview
Walks a directory of CSV and Parquet files, applies the schema in `Resources/schema.json`, and emits a per-row coverage report.

## Goals
- Detect schema drift across daily dataset drops before downstream consumers notice.
- Produce a deterministic markdown coverage report under `reports/`.
- Surface the top three slowest validations to inform schema-level optimisation.

## Instructions
- MUST validate every file declared in the dataset manifest before producing the summary.
- ALWAYS use streaming readers so files larger than memory still validate end-to-end.
- DO NOT mutate the input dataset directory; treat it as strictly read-only.
- Prefer Parquet over CSV when both formats are available for the same dataset.

## Notes
- Strictly forbidden to write generated reports back to the input dataset directory.
- Never expose row-level personal data inside the public coverage summary.

## Caveats
- The validator skips empty files with a warning rather than a hard failure.
