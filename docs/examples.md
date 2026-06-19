# Examples

## Minimal intent.yaml

```yaml
version: "1.0"
agent:
  name: "my-agent"
  type: "custom"
  description: "A simple agent"
intent: {}
```

## Coding Agent

```yaml
version: "1.0"
agent:
  name: "code-reviewer"
  type: "coding"
  description: "Reviews PRs for code quality and security"
intent:
  goals:
    - description: "Identify bugs and security vulnerabilities"
      priority: "high"
    - description: "Suggest improvements with clear rationale"
      priority: "medium"
  non_negotiables:
    - rule: "Never approve code with hardcoded secrets"
      severity: "hard"
  tools:
    allowed:
      - name: "github_api"
        rationale: "Required for PR review"
    denied:
      - name: "production_deployer"
        rationale: "Deployment requires human approval"
```

## Using Templates

```bash
# List available templates
intentspec init --template list

# Create from template
intentspec init --template data-pipeline --name my-etl

# Create from CrewAI config
intentspec init --from crewai.yaml ./crewai.yaml
```

## CI/CD Integration

```bash
# Run all checks
intentspec ci --min-coverage 80 --strict

# In GitHub Actions
- uses: onicarps/intentspec-action@v1
  with:
    min-coverage: 80
    strict: true
```
