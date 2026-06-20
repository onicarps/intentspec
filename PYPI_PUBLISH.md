# PyPI Publish Checklist

## Status: BLOCKED — 403 Forbidden

## What Works
- Package builds successfully: `python -m build` → wheel (68KB) + sdist
- All 775 tests pass
- Package installs locally: `pip install dist/intentspec-0.1.0-py3-none-any.whl`
- All 11 commands verified working from built wheel
- Package name `intentspec` is available on PyPI (no existing package)

## What Doesn't Work
- `twine upload` returns 403 Forbidden
- Token format is valid (starts with `pypi-`, 120 chars)
- Token is set as `PYPI_API_TOKEN` environment variable

## Root Cause
The `PYPI_API_TOKEN` environment variable contains a valid-format PyPI API token but it either:
1. Belongs to a different PyPI account
2. Has been revoked or expired
3. Was created without "Upload" scope

## Action Required
1. Go to https://pypi.org/manage/account/token/
2. Create a new API token with "Upload" scope for the `intentspec` project
3. Set the token: `export PYPI_API_TOKEN=pypi-...`
4. Rebuild: `python -m build`
5. Publish: `twine upload dist/intentspec-0.1.0-py3-none-any.whl`

## Alternative: TestPyPI First
```bash
twine upload --repository testpypi dist/intentspec-0.1.0-py3-none-any.whl
pip install --index-url https://test.pypi.org/simple/ intentspec
```
