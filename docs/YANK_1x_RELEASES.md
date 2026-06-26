# Yank mistaken 1.x PyPI releases (required)

`pip install intentspec` resolves to the **highest** version. Because `1.3.1 > 0.3.0`, users still get 1.x until these are yanked.

## Yank via PyPI web UI

1. Open https://pypi.org/manage/project/intentspec/releases/
2. For each version **1.2.0**, **1.3.0**, **1.3.1**:
   - Options → **Yank**
   - Reason: `Incorrect semver; canonical pre-1.0 line is 0.3.x`

## Verify

```bash
pip index versions intentspec   # should show 0.3.0 as latest among non-yanked
pip install intentspec          # should install 0.3.0
intentspec --version            # 0.3.0
```

## Interim install (before yank)

```bash
pip install 'intentspec>=0.3,<1'
```