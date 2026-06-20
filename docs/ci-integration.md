# CI/CD Integration

Guide for integrating IntentSpec into CI/CD pipelines.

## Quick Start

```bash
# Run all checks
intentspec ci

# With minimum coverage threshold
intentspec ci --min-coverage 80

# Strict mode — fail on warnings
intentspec ci --strict

# JSON output for machine parsing
intentspec ci --format json
```

## Exit Codes

| Code | Meaning | When |
|------|---------|------|
| 0 | Pass | All checks pass |
| 1 | Error | Schema validation, semantic error, or lint error |
| 2 | Warning | Stale spec, sparse coverage |
| 3 | Fatal | Missing spec or below `--min-coverage` threshold |

## GitHub Action

Use the official GitHub Action in your workflow:

```yaml
name: IntentSpec CI
on: [pull_request]

jobs:
  intentspec:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: onicarps/intentspec-action@v1
        with:
          min-coverage: 80
          strict: true
```

The action:
1. Installs `intentspec` from PyPI
2. Runs `intentspec ci` with your specified options
3. Posts a PR comment with score and coverage results

## GitLab CI

```yaml
intentspec:
  image: python:3.12
  script:
    - pip install intentspec
    - intentspec ci --min-coverage 80 --strict
  only:
    - merge_requests
```

## Pre-commit Hook

Add to `.pre-commit-hooks.yaml` in your repo:

```yaml
- repo: https://github.com/onicarps/intentspec
  rev: v0.1.0
  hooks:
    - id: intentspec-validate
      stages: [commit]
```

Or use the built-in hook config:

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: intentspec
        name: IntentSpec Validate
        entry: intentspec validate --strict
        language: python
        additional_dependencies: [intentspec]
        files: intent\.yaml$
```

## Generic CI (Jenkins, CircleCI, Azure DevOps)

Use exit codes for integration:

```bash
# Basic
intentspec ci
EXIT_CODE=$?

# With options
intentspec ci --min-coverage 80 --strict --format json > results.json
EXIT_CODE=$?

# Use in pipeline
if [ $EXIT_CODE -eq 0 ]; then
  echo "All checks passed"
elif [ $EXIT_CODE -eq 3 ]; then
  echo "Coverage below threshold"
  exit 1
fi
```

## Configuration

Create `.intentspec.yaml` in your repo root:

```yaml
# Minimum coverage percentage (0-100)
min_coverage: 80

# Treat warnings as errors
strict: false

# Default output format: text, json, yaml
format: text
```

Config precedence: CLI flags > env vars > `.intentspec.yaml` > defaults

### Environment Variables

| Variable | Description |
|----------|-------------|
| `INTENTSPEC_MIN_COVERAGE` | Override min_coverage |
| `INTENTSPEC_STRICT` | Override strict mode (true/false) |
| `INTENTSPEC_FORMAT` | Override output format |

## Docker

```dockerfile
FROM python:3.12-slim
RUN pip install intentspec
COPY . /workspace
WORKDIR /workspace
CMD ["intentspec", "ci", "--strict"]
```

```bash
docker build -t intentspec-ci .
docker run --rm -v $(pwd):/workspace intentspec-ci
```
