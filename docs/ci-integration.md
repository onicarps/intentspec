# CI Integration Guide

This guide explains how to wire `intentspec ci` into any CI/CD system. The command is designed as a drop-in CI gate: it aggregates validation, linting, scoring, and coverage checks into a single exit code, so your pipeline can simply run the command and let the exit code decide pass or fail.

## Exit Codes

`intentspec ci` returns one of four exit codes. Your CI job's pass/fail status is driven entirely by this code.

| Code | Meaning | Trigger |
|------|---------|---------|
| **0** | Pass | No errors, no warnings, coverage meets threshold |
| **1** | Validation error | Schema or semantic errors, lint errors; under `--strict` also any warning |
| **2** | Warning | Warnings only (semantic/lint), non-strict mode |
| **3** | Fatal | Spec file missing, empty, or unreadable; coverage below `--min-coverage` threshold; malformed `--config` |

Aggregation across multiple files uses rank order (highest wins): **fatal (3) > error (1) > warning (2) > pass (0)**.

## CLI Flags

```
intentspec ci [OPTIONS] [PATHS]...
```

| Flag | Description |
|------|-------------|
| `--min-coverage N` | Minimum coverage threshold (0-100). Exit 3 if computed coverage is below N. |
| `--strict` | Promote warnings to errors. Exit 2 never occurs under `--strict`. |
| `--config PATH` | Path to a `.intentspec.yaml` config file. Overrides auto-discovered config. |
| `--format FORMAT` | Output format: `text` (default), `json`, or `yaml`. |

`PATHS` are files or directories to check. Directories are globbed for `**/intent.yaml`. Defaults to `.` when no path is given.

## Reproducing Exit Codes

Each exit code can be reproduced from the command line:

**Exit 0 — valid spec:**
```bash
intentspec ci tests/fixtures/valid_intent.yaml
echo $?  # 0
```

**Exit 1 — schema-invalid spec:**
```bash
intentspec ci tests/fixtures/invalid_intent.yaml
echo $?  # 1
```

**Exit 2 — warning-only spec (non-strict):**
```bash
# A spec with a short agent description triggers a lint warning
cat > /tmp/warning_spec.yaml << 'EOF'
version: "1.0"
agent:
  name: "short-bot"
  type: "coding"
  description: "Short"
intent:
  goals:
    - description: "A short goal"
      priority: "medium"
  constraints:
    - rule: "Always be helpful"
      enforceable: true
  non_negotiables:
    - rule: "Never harm users"
      severity: "hard"
  tools:
    allowed:
      - name: "cli"
        rationale: "Command line access"
    denied: []
EOF
intentspec ci /tmp/warning_spec.yaml
echo $?  # 2
```

**Exit 3 — missing spec:**
```bash
intentspec ci /nonexistent/path.yaml
echo $?  # 3
```

**Exit 3 — coverage below threshold:**
```bash
intentspec ci tests/fixtures/valid_intent.yaml --min-coverage 100
echo $?  # 3
```

## Usage Snippets

### Jenkins

```groovy
pipeline {
  agent any

  stages {
    stage('Intent Spec') {
      steps {
        sh 'pip install intentspec'
        sh 'intentspec ci --min-coverage 50 --strict'
      }
    }
  }

  post {
    success {
      echo 'IntentSpec CI: all checks passed (exit 0)'
    }
    failure {
      echo 'IntentSpec CI: checks failed (exit 1, 2, or 3)'
    }
  }
}
```

Jenkins treats any non-zero exit code as a build failure by default. The `sh` step propagates the exit code directly, so the stage fails when `intentspec ci` returns 1, 2, or 3.

If you want to distinguish warnings (exit 2) from hard failures (exit 1 or 3), use a scripted approach:

```groovy
pipeline {
  agent any

  stages {
    stage('Intent Spec') {
      steps {
        sh 'pip install intentspec'
        script {
          def exitCode = sh script: 'intentspec ci --min-coverage 50; echo \$?', returnStdout: true
          def code = exitCode.trim().toInteger()
          if (code == 3) {
            error 'IntentSpec CI: fatal — missing spec or below coverage threshold'
          } else if (code == 1) {
            error 'IntentSpec CI: validation errors detected'
          } else if (code == 2) {
            echo 'IntentSpec CI: warnings detected (exit 2)'
            // Mark build as unstable instead of failed
            currentBuild.result = 'UNSTABLE'
          }
        }
      }
    }
  }
}
```

### CircleCI

```yaml
version: 2.1

jobs:
  intentspec-ci:
    docker:
      - image: python:3.11
    steps:
      - checkout

      - run:
          name: Install intentspec
          command: pip install intentspec

      - run:
          name: Run intentspec ci
          command: intentspec ci --min-coverage 50 --strict
```

CircleCI fails the job when any `run` step exits non-zero, so the `intentspec ci` exit code drives pass/fail directly. To treat exit code 2 (warning) as a soft failure, add a step that inspects the code:

```yaml
version: 2.1

jobs:
  intentspec-ci:
    docker:
      - image: python:3.11
    steps:
      - checkout

      - run:
          name: Install intentspec
          command: pip install intentspec

      - run:
          name: Run intentspec ci (allow warnings)
          command: |
            intentspec ci --min-coverage 50
            exit_code=$?
            if [ $exit_code -eq 3 ]; then
              echo "FATAL: missing spec or below coverage threshold"
              exit 1
            elif [ $exit_code -eq 1 ]; then
              echo "ERROR: validation errors"
              exit 1
            elif [ $exit_code -eq 2 ]; then
              echo "WARNING: warnings detected"
              exit 0
            fi
```

### Azure DevOps

```yaml
trigger:
  - main

pool:
  vmImage: ubuntu-latest

steps:
  - script: pip install intentspec
    displayName: Install intentspec

  - script: intentspec ci --min-coverage 50 --strict
    displayName: Run intentspec ci
```

Azure Pipelines fails the task when `script` steps exit non-zero, so the `intentspec ci` exit code governs the task result directly. To differentiate exit code 2 (warning) from hard failures:

```yaml
trigger:
  - main

pool:
  vmImage: ubuntu-latest

steps:
  - script: pip install intentspec
    displayName: Install intentspec

  - script: |
      intentspec ci --min-coverage 50
      exit_code=$?
      if [ $exit_code -eq 3 ]; then
        echo "##vso[task.logissue type=error]FATAL: missing spec or below coverage threshold"
        exit 1
      elif [ $exit_code -eq 1 ]; then
        echo "##vso[task.logissue type=error]Validation errors detected"
        exit 1
      elif [ $exit_code -eq 2 ]; then
        echo "##vso[task.logissue type=warning]Warnings detected (exit 2)"
        exit 0
      fi
    displayName: Run intentspec ci
```

The `##vso[task.logissue]` logging command surfaces warnings and errors in the Azure DevOps build timeline.

## Config File

`intentspec ci` reads `.intentspec.yaml` from the working directory automatically, or an explicit file via `--config PATH`. Supported keys:

```yaml
min_coverage: 50    # equivalent to --min-coverage 50
strict: true        # equivalent to --strict
format: json        # equivalent to --format json
```

Precedence (highest wins): **CLI flag > environment variable > config file > built-in default**.

Environment variables: `INTENTSPEC_MIN_COVERAGE`, `INTENTSPEC_STRICT`, `INTENTSPEC_FORMAT`.

## Combining with Other Integrations

For GitHub Actions, see the composite action in `action/action.yml` and the example workflow in `.github/workflows/intentspec.yml`. For GitLab CI, see `.gitlab-ci.yml`. For pre-commit, see `.pre-commit-hooks.yaml`.
