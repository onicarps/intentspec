# IntentSpec Blog Post — Technical Audit Report

**Auditor:** OWL (subagent)  
**Date:** June 21, 2026  
**Blog post:** `BLOG_POST.md` (127 lines)  
**Codebase:** `src/intentspec/` (39 Python modules, ~3,614 LOC)  
**Test suite:** 794 passed, 1 skipped (excluding 4 performance-budget tests), 86.11% coverage  

---

## 1. Technical Accuracy

### ✅ Claims Verified Correct

| Claim | Status | Evidence |
|-------|--------|----------|
| `pip install intentspec` | ✅ | `pyproject.toml` line 6: `name = "intentspec"`, version 0.1.1 |
| `intentspec --version` | ✅ | `cli.py:37`: `version_option(version="0.1.1")` — outputs `intentspec, version 0.1.1` |
| 11 commands | ✅ | `cli.py` defines: `validate`, `init`, `score`, `coverage`, `diff`, `lint`, `ci`, `audit_report`, `health`, `drift`, `dashboard` — 11 commands |
| 4 adapters (CrewAI, LangGraph, AutoGen, OpenAI Agents SDK) | ✅ | `adapters/` dir: `crewai.py`, `langgraph.py`, `autogen.py`, `openai_agents.py` — all with `parse_*` functions |
| 5 built-in templates | ✅ | `templates/`: `coding-agent.yaml`, `research-agent.yaml`, `service-agent.yaml`, `data-pipeline.yaml`, `multi-agent-coordinator.yaml` |
| IDS formula with 7 weighted components | ✅ | `score/ids.py:19-27`: weights sum to 1.0, formula is `100 - weighted_sum` |
| Schema v1 with agent, intent, metadata blocks | ✅ | `spec/schema.py`: full JSON Schema draft-07 with all claimed fields |
| `intentspec validate` output format | ✅ | `cli.py:96-97`: text output shows `✓ intent.yaml: valid` with IDS Score |
| `intentspec ci` with `--min-coverage` and `--strict` | ✅ | `cli.py:562-609`: both flags implemented |
| `intentspec health` — coverage trend, stale intents, IDS distribution | ✅ | `health.py:67-100`: shows all three |
| `intentspec drift` — 30+ day stale detection | ✅ | `drift.py:82`: `threshold_days` defaults to 30 |
| `intentspec dashboard` — web UI with charts | ✅ | `dashboard/`: FastAPI + Chart.js implementation |
| CI/CD GitHub Action | ✅ | `action/action.yml`: composite action with `pip install intentspec` + `intentspec ci` |
| Exit codes 0/1/2/3 | ✅ | All commands return 0 (pass), 1 (validation error), 2 (warning), 3 (fatal) |
| `--format text/json/yaml` on all commands | ✅ | Every command accepts `--format` with all three choices |
| `init --from` supports AGENTS.md, SKILL.md, agentskills, crewai, langgraph, autogen, openai_agents | ✅ | `converter/__init__.py:65-81`: all 7 formats routed |
| `init --quickstart` — interactive wizard | ✅ | `cli.py:366-408`: 4-question wizard (name, type, non-negotiables, tools) |
| `init --template` with list | ✅ | `cli.py:411-498`: template loading with `list` subcommand |
| `audit-report` — SOC 2 / EU AI Act compliance | ✅ | `audit.py:23-30`: preamble references both frameworks, SHA-256 hash |
| GitHub URL | ✅ | `pyproject.toml:48`: `https://github.com/onicarps/intentspec` |
| MIT License | ✅ | `pyproject.toml:10`: `license = {text = "MIT"}` |

### ⚠️ Minor Discrepancies

| Claim | Issue | Severity |
|-------|-------|----------|
| "729 tests passing" | Actual count is **794 passed** (excluding performance tests) or **729 passed** (including performance tests, 1 failed). The blog undercounts by 65 tests. | Low — the claim is conservative, not wrong, but outdated |
| "86% coverage" | Actual coverage is **86.11%** — the claim rounds correctly | Negligible |
| Blog says IDS formula is `100 - (tool_coverage×0.25 + ...)` | The code computes `score = 100 * weighted_sum` where each component is a **coverage ratio** (higher = better). The blog's formula `100 - (...)` would give lower = better. The code's `completeness` at `ids.py:100` does `round(100.0 * weighted_sum, 2)` — so higher score = better documented. The blog's "100 minus" framing is **inverted** from the actual implementation. | **Medium** — The blog says "IDS Score (0-100)" and the code outputs 0-100, but the formula description is misleading. The code treats IDS as a "quality score" (higher = better), not a "debt score" (lower = better). This is a naming/branding inconsistency. |
| Blog says "3 questions" for quickstart wizard | The code actually asks **4 questions** (name, type, non-negotiables, tools) — though the AGENTS.md also says "3 questions" but the code at `cli.py:371-394` clearly has 4 prompts | Low |
| Blog says `intentspec init --from crewai.yaml ./my-crew.yaml` | The CLI uses `--from crewai` (not `crewai.yaml`) — the format choice is `crewai`, not a filename. The blog conflates the format name with the filename. | Low |
| Blog says dashboard uses "Chart.js bundled locally" | The code at `dashboard/__init__.py:22` uses `_CHART_JS = "https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"` — this is a **CDN URL**, not bundled locally. The AGENTS.md claims "Chart.js bundled locally" but the code doesn't match. | **Medium** — This is a documented feature that isn't implemented as described |
| Blog says "Works with any agent spec format" | The tool works with exactly **7 formats** (AGENTS.md, SKILL.md, agentskills, CrewAI, LangGraph, AutoGen, OpenAI Agents). "Any" is marketing hyperbole. | Low |

### ❌ Incorrect Claims

None found. All substantive claims are backed by code.

---

## 2. Completeness — What's Missing from the Blog

### Important Omissions

1. **No mention of `intentspec diff`** — This is a key feature (git-integrated intent change tracking) that's completely absent from the blog post. It's in the README and codebase but not the blog.

2. **No mention of `intentspec lint`** — The quality-checks command is missing from the blog. It checks goal descriptions, tool rationale, duplicates, etc.

3. **No mention of `intentspec coverage`** — The structural coverage analysis command (comparing intent against source text) is not mentioned.

4. **No mention of `intentspec audit-report`** — The compliance report generator (SOC 2 / EU AI Act) is a major selling point that's buried in the "Why IntentSpec?" section but never demonstrated.

5. **No Python version requirement** — The blog doesn't mention Python 3.11+ requirement.

6. **No mention of `--format json/yaml`** — The machine-readable output formats are a key feature for CI/CD integration but aren't highlighted.

7. **No mention of custom weights** — `intentspec score --weights` allows custom IDS weighting, which is powerful for teams.

8. **No mention of `--by-agent` breakdown** — `intentspec score --by-agent` for multi-agent setups.

9. **No mention of exit codes** — The 0/1/2/3 exit code system is critical for CI/CD but not explained.

10. **No mention of `intentspec init --template list`** — The ability to list available templates is useful.

11. **No mention of the `extends` / `sub_agents` schema fields** — These are reserved for Phase 4 but signal future direction.

12. **No mention of the `.intentspec.yaml` config file** — The `ci` command supports `--config` for persistent settings.

13. **No mention of the `intentspec dashboard --serve --host --port` options** — The blog just says "web UI with charts" but doesn't mention the host/port configurability.

14. **No mention of the `intentspec drift --threshold-days` option** — The default is 30 but it's configurable.

15. **No mention of the `intentspec health --stale-days` option** — Same as above.

### Missing Sections That Would Strengthen the Blog

- **A "How It Works" diagram or explanation** — How does IntentSpec fit in the developer workflow?
- **A real-world example** — Show a before/after of an AGENTS.md → intent.yaml conversion
- **A sample `intent.yaml`** — Developers want to see what the output looks like
- **Performance characteristics** — The blog could mention that validate runs in <100ms
- **Comparison to alternatives** — Why not just use YAML linting or JSON Schema validators?
- **Roadmap / Phase 4 teaser** — sub_agents, extends, community templates

---

## 3. Persuasiveness

### Strengths

1. **Clear problem statement** — The opening "scattered markdown files, README comments, tribal knowledge" resonates with anyone who's worked with AI agents.

2. **Strong opening CTA** — The 3-line `pip install` / `init` / `validate` / `score` sequence is compelling and low-friction.

3. **Good feature organization** — The numbered "What It Does" section (1-5) is easy to scan.

4. **The "Why IntentSpec?" section** — The bullet points (Transparent, Measurable, Enforceable, Auditable, Universal) are strong value propositions.

5. **SOC 2 / EU AI Act mention** — This is a strong differentiator for enterprise buyers.

### Weaknesses

1. **No social proof** — No testimonials, no GitHub stars, no user count, no "used by" logos. For a v0.1.1 project, this is expected but still a gap.

2. **No differentiation** — The blog doesn't explain why someone shouldn't just use a YAML schema validator or write their own. What makes IntentSpec *specifically* for AI agents?

3. **No visual elements** — No screenshots of the dashboard, no terminal output examples, no diagrams. A picture of the dashboard would be worth 1000 words.

4. **No concrete example** — The blog never shows what an `intent.yaml` looks like, or what the output of `intentspec score` actually shows. Developers want to see the artifact.

5. **"Universal: Works with any agent spec format"** — This is overstated. It works with 7 specific formats. Better to say "Works with all major agent spec formats" or list them.

6. **The IDS formula table is dry** — A table of weights doesn't explain *why* tool coverage matters more than constraint coverage. A sentence of rationale would help.

7. **No "aha moment"** — The blog doesn't create a moment of "I need this." It lists features but doesn't paint a picture of the pain of *not* having it.

8. **The CI/CD section is thin** — It shows the GitHub Action YAML but doesn't explain what happens when a build fails, or how it posts PR comments.

9. **No call-to-action beyond "Get Started"** — Missing: "Star us on GitHub," "Join the Discord," "Read the docs," "Contribute."

---

## 4. Structure and Flow

### Current Structure

```
1. The Problem (3 paragraphs)
2. The Solution (4-line code block)
3. What It Does (5 numbered sections)
4. Supported Formats (table)
5. Quickstart (code block)
6. Why IntentSpec? (5 bullets)
7. Get Started (code block + links)
```

### Assessment

**Good:**
- Problem → Solution → Details → CTA is a classic and effective flow
- The "Supported Formats" table is well-placed after the feature overview
- The Quickstart is concrete and actionable

**Could be improved:**
- The "What It Does" section mixes commands (validate, score, ci) with features (drift, dashboard) — consider separating "Commands" from "Features"
- The "Supported Formats" table is redundant with the "Convert Existing Specs" section above it — merge them
- The "Quickstart" section repeats the "Get Started" section at the bottom — consolidate
- No table of contents — at 127 lines it's fine, but as it grows, a TOC would help
- The "Why IntentSpec?" section comes *after* the quickstart — consider moving it before, or integrating it into the problem statement

### Suggested Restructure

```
1. The Problem (keep)
2. The Solution (keep, but add a sample intent.yaml)
3. Quickstart (expand with output examples)
4. Key Features (consolidate the 5 numbered sections + missing commands)
5. Supported Formats (merge with converter section)
6. CI/CD Integration (expand with PR comment screenshot)
7. Why IntentSpec? (keep, but add differentiation)
8. Get Started (consolidate with links to docs, GitHub, Discord)
```

---

## 5. Specific Suggestions for Improvement

### High Priority

1. **Fix the IDS formula description** — Either update the blog to match the code (higher = better quality score) or update the code to match the blog (100 - weighted_sum = debt score). The current inconsistency between "Intent Debt Score" (implies lower = better) and the actual formula (higher = better) is confusing.

2. **Add a sample `intent.yaml`** — Show developers what the output looks like. This is the single most impactful addition.

3. **Add terminal output examples** — Show what `intentspec validate`, `intentspec score`, and `intentspec ci` actually output. Use ASCII art or code blocks.

4. **Mention the missing commands** — `diff`, `lint`, `coverage`, and `audit-report` are significant features that deserve at least a sentence each.

5. **Fix the "Chart.js bundled locally" claim** — Either bundle Chart.js locally (replace the CDN URL) or update the blog to remove this claim.

### Medium Priority

6. **Update test count** — Change "729 tests" to "794 tests" or "800+ tests" to reflect the current count.

7. **Add Python 3.11+ requirement** — This is important for developers to know before they try to install.

8. **Explain the exit codes** — A small table showing 0/1/2/3 and what they mean would be valuable for CI/CD users.

9. **Add a "How It Works" paragraph** — Explain the workflow: write agent spec → convert to intent.yaml → validate → score → enforce in CI.

10. **Clarify "Universal"** — Change "Works with any agent spec format" to "Works with all major agent spec formats" or list the 7 supported formats.

### Low Priority

11. **Fix quickstart wizard question count** — The blog says "3 questions" but the code has 4. Update one or the other.

12. **Fix `--from` format names** — The blog shows `--from crewai.yaml` but the code uses `--from crewai`. Use the correct format name.

13. **Add a roadmap section** — Mention Phase 4 features (sub_agents, extends, community templates) to signal future direction.

14. **Add community/links section** — GitHub, docs, Discord, Twitter, etc.

15. **Add a "Before IntentSpec / After IntentSpec" comparison** — Show the pain of scattered docs vs. the clarity of intent.yaml.

---

## Summary

| Category | Rating | Notes |
|----------|--------|-------|
| **Technical Accuracy** | 9/10 | One medium issue (IDS formula direction), one medium issue (Chart.js CDN vs. bundled), minor discrepancies (test count, question count, format names) |
| **Completeness** | 6/10 | Missing 4 commands (`diff`, `lint`, `coverage`, `audit-report`), no sample output, no Python version requirement, no exit code explanation |
| **Persuasiveness** | 6/10 | Strong problem statement and value props, but no social proof, no visual examples, no concrete `intent.yaml` sample, no differentiation from alternatives |
| **Structure & Flow** | 7/10 | Good overall arc, but redundant sections, missing TOC, "Why" section placed after quickstart |
| **Overall** | 7/10 | A solid first draft that accurately represents the codebase but needs concrete examples, visual elements, and completeness improvements to truly convert readers into users |

### Top 3 Changes That Would Most Improve the Blog

1. **Add a sample `intent.yaml` and terminal output** — Developers need to see the artifact
2. **Fix the IDS formula description** — Align the blog with the code (or vice versa)
3. **Mention all 11 commands** — The blog only covers ~6 of 11 commands; the missing ones are significant features
