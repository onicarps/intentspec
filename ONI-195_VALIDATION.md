# ONI-195 Phase 2A Gate Validation Report

**Automatable criteria:** PASS

| Criterion | Threshold | Measured | Status |
|-----------|-----------|----------|--------|
| MCP enforcement FP rate | <20% | 0.0% (0/3 aligned scenarios) | ✅ pass |
| Lint rules FP rate (proxy) | <15% on valid specs | 0.0% (0/1 valid specs with lint errors) | ✅ pass |
| Converter accuracy | ≥75% | 100.0% (15 fixtures) | ✅ pass |
| Schema migration | all v1.0 fixtures migrate cleanly | 1 ok, 0 failed | ✅ pass |
| Framework adapter accuracy | ≥70% per adapter | 93.8% average across 4 adapters | ✅ pass |
| EU AI Act pack completeness | ≥80% Annex IV (legal review) | deferred to Phase 3 | ⏳ pending |
| GitHub stars | ≥200 at 3 months | monitor monthly (ONI-196) | ⏳ pending |
| Lint external review | <15% FP with 5 reviewers | proxy check above | ⏳ pending |

### MCP enforcement FP rate
- OK: aligned-filesystem correctly aligned
- OK: aligned-terminal correctly aligned
- OK: aligned-search correctly aligned
- OK: gap-extra-tools correctly flagged
- OK: denied-on-server correctly flagged

### Converter accuracy
- complex/SKILL: 100.0%
- sample_agents_md/autogpt: 100.0%
- sample_agents_md/edge-bom: 100.0%
- sample_agents_md/edge-empty: 100.0%
- sample_agents_md/edge-malformed: 100.0%
- sample_agents_md/edge-non-english: 100.0%
- sample_agents_md/edge-recursive: 100.0%
- sample_agents_md/kubernetes: 100.0%
- sample_agents_md/langchain: 100.0%
- sample_agents_md/promptfoo: 100.0%
- sample_agents_md/vercel-ai: 100.0%
- sample_agents_md/workspace-agents: 100.0%
- sample_skills_md/complex: 100.0%
- sample_skills_md/simple: 100.0%
- simple/SKILL: 100.0%

### Schema migration
- Migrated: tests/fixtures/sample_agents_md/intent.yaml

### Framework adapter accuracy
- crewai: 91.7% (3 configs)
- langgraph: 100.0% (3 configs)
- autogen: 91.7% (3 configs)
- openai_agents: 91.7% (3 configs)

### EU AI Act pack completeness
- Requires legal/compliance review — not automatable

### GitHub stars
- Leading adoption indicator — track via PDD kill criteria review

### Lint external review
- Full gate requires 5 external developer reviews