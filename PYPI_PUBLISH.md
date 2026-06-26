# PyPI Publish — GitHub OIDC (Trusted Publishing)

## Status: ACTIVE — canonical pre-1.0 line is **0.3.x**

## Versioning
- **0.1.x** — early alpha
- **0.3.0** — Phase 2 complete (current)
- **1.0.0** — reserved for public launch after beta
- Mistaken **1.2.0 / 1.3.0 / 1.3.1** publishes are **yanked**

## Publish a release
```bash
cd ~/.hermes/profiles/intentspec/workspace
# version in pyproject.toml, __init__.py, cli.py
python3 -m pytest tests/ -q
git commit -am "chore: release 0.3.x"
git tag v0.3.x
git push origin main && git push origin v0.3.x
```

Workflow `.github/workflows/publish.yml` runs on `v*` tags.

## After publishing
```bash
pip install --upgrade intentspec
intentspec --version
```