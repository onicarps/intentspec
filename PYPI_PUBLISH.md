# PyPI Publish — Using GitHub OIDC (Trusted Publishing)

## Status: READY — GitHub Actions workflow created

## How It Works
Unlike the old API token approach, this uses GitHub's OIDC provider for authentication.
No API token needed — GitHub provides a short-lived token to PyPI during the workflow.

## What's Done
- `.github/workflows/publish.yml` — triggers on tags `v*`, builds + publishes via OIDC
- Package builds successfully: `python -m build` → wheel (68KB) + sdist

## What's Needed
1. Go to https://pypi.org/manage/account/publishing/
2. Create a new pending publisher:
   - **PyPI Project Name:** `intentspec`
   - **Owner:** `onicarps`
   - **Repository name:** `intentspec`
   - **Workflow name:** `publish.yml`
   - **Environment name:** `pypi`
3. Push a tag to trigger publish:
   ```bash
   cd ~/.hermes/profiles/intentspec/workspace
   git tag v0.1.0
   git push origin v0.1.0
   ```

## After Publishing
```bash
pip install intentspec
intentspec --version
```

## Why This Works (and API Tokens Don't)
The `PYPI_API_TOKEN` env var has a valid token but it's either:
- Scoped to a different PyPI account
- Missing "Upload" permission
- Expired/revoked

The OIDC approach doesn't need any token — GitHub and PyPI establish trust via OpenID Connect.
