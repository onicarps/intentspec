# PyPI Publish — Using GitHub OIDC (Trusted Publishing)

## Status: ACTIVE — v1.3.1 published June 26 2026

## How It Works
GitHub OIDC trusted publishing — no long-lived API token. Push a `v*` tag → workflow builds and publishes.

## What's Done
- `.github/workflows/publish.yml` — triggers on tags `v*`
- Published: **v1.2.0**, **v1.3.0**, **v1.3.1**
- Current PyPI latest: **1.3.1**

## To publish a new release
```bash
cd ~/.hermes/profiles/intentspec/workspace
# bump version in pyproject.toml, __init__.py, cli.py
python3 -m pytest tests/ -q
git commit -am "chore: release vX.Y.Z"
git tag vX.Y.Z
git push origin main
git push origin vX.Y.Z
```

## After Publishing
```bash
pip install --upgrade intentspec
intentspec --version   # expect latest
```

## OIDC setup (one-time)
https://pypi.org/manage/account/publishing/ — publisher for `onicarps/intentspec`, workflow `publish.yml`, environment `pypi`.