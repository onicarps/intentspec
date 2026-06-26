# Mission: IntentSpec v1.3.0 — Post-Fix Re-Targeted Test

## Your Task

Grok has applied fixes. Run a focused re-test of the 4 previously broken bugs. Execute ALL commands from `/home/oni/.hermes/profiles/intentspec/workspace`.

## Bugs to Re-Test

### BUG-1: `init --template` was broken (templates not in installed package)
```bash
cd /home/oni/.hermes/profiles/intentspec/workspace
intentspec init --template list
intentspec init --template coding-agent -y -o /tmp/test_template.yaml
intentspec validate /tmp/test_template.yaml
```
Expected: Lists templates, creates file, validates OK

### BUG-2: `gate` crashed with FileNotFoundError
```bash
cd /home/oni/.hermes/profiles/intentspec/workspace
intentspec gate .
```
Expected: Clean report or graceful error (no traceback)

### BUG-3: `--format json/yaml` unparseable on some commands
```bash
cd /home/oni/.hermes/profiles/intentspec/workspace
intentspec diff tests/fixtures/valid_intent.yaml --format json | python3 -c "import sys,json; json.load(sys.stdin); print('JSON OK')"
intentspec diff tests/fixtures/valid_intent.yaml --format yaml | python3 -c "import sys,yaml; yaml.safe_load(sys.stdin); print('YAML OK')"
intentspec migrate tests/fixtures/valid_intent.yaml --format json | python3 -c "import sys,json; json.load(sys.stdin); print('JSON OK')"
intentspec test tests/fixtures/valid_intent.yaml --format json | python3 -c "import sys,json; json.load(sys.stdin); print('JSON OK')"
```
Expected: All 4 print "OK"

### BUG-4: Inconsistent exit codes for missing paths
```bash
cd /home/oni/.hermes/profiles/intentspec/workspace
for cmd in validate lint score coverage drift test; do
  intentspec $cmd /tmp/does_not_exist_xyz.yaml >/dev/null 2>&1
  echo "$cmd: exit=$?"
done
```
Expected: All exit 3

## Report Format

```
# IntentSpec v1.3.0 — Post-Fix Re-Test

## Results
| Bug | Status | Evidence |
|-----|--------|----------|
| BUG-1 (init --template) | ✅/❌ | ... |
| BUG-2 (gate crash) | ✅/❌ | ... |
| BUG-3 (format parse) | ✅/❌ | ... |
| BUG-4 (exit codes) | ✅/❌ | ... |

## Overall: PASS / PARTIAL / FAIL
```

Save to `/home/oni/.hermes/profiles/intentspec/workspace/INTENTSPEC_V130_RETEST_v2.md`

## Constraints
- Do NOT modify source code
- Do NOT write new tests
- Run ALL commands from `/home/oni/.hermes/profiles/intentspec/workspace`
- Use `intentspec` CLI (installed)
