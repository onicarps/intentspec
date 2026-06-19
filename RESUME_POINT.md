# IntentSpec Resume Point — June 20 2026 (W5 In Progress)

## State: Week 5 Droid mission running (launched ~00:15)

### Droid Mission
- ID: f428a9bb-63a2-4c10-af74-e2af9c410291
- State: running
- Completed: lint-baseline
- In progress: audit-report
- Pending: templates, init-template, crewai-adapter, coverage-uplift, docs-and-readme
- Notify on complete: yes

### To Check Status
```bash
cat ~/.factory/missions/f428a9bb-63a2-4c10-af74-e2af9c410291/state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['state'])"
cat ~/.factory/missions/f428a9bb-63a2-4c10-af74-e2af9c410291/features.json | python3 -c "import sys,json; [print(f\"[{f.get('status','?'):12s}] {f.get('id','?')}\") for f in json.load(sys.stdin).get('features',[])]"
cd ~/.hermes/profiles/intentspec/workspace && git log --oneline -10
python3 -m pytest tests/ -q
```

### When Droid Finishes
1. Review all new code for mechanical bugs
2. Run full test suite: python3 -m pytest tests/ -q
3. Run lint: ruff check src/intentspec tests
4. Run coverage: pytest --cov=src/intentspec --cov-fail-under=88
5. Test CLI manually: intentspec audit-report, init --template, etc.
6. Verify mkdocs build: mkdocs build
7. Commit, push, update memory

### Week 5 Tasks (if Droid pauses early, complete manually)
- src/intentspec/audit.py — generate_audit() function
- src/intentspec/templates/data-pipeline.yaml
- src/intentspec/templates/multi-agent-coordinator.yaml
- src/intentspec/adapters/crewai.py — parse_crewai() + wire into converter
- tests/test_audit.py, test_templates.py, test_adapters.py
- docs/ mkdocs site + README update
- Coverage uplift to ≥88%

### After W5: Week 6-7
- TestPyPI gate, PyPI publish, beta program (5-10 users)

### Environment
- Working dir: ~/.hermes/profiles/intentspec/workspace/
- pip install -e ".[dev]" --break-system-packages
