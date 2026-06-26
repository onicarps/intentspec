# We Analyzed 22 Agent Specs. Most Never Say What Tools Are Forbidden.

*Coverage analysis for agent behavior — not another prompt framework.*

When you ship an AI agent, how do you know it won't do something you never intended? Most teams answer with a markdown file: `AGENTS.md`, `SKILL.md`, or a framework config. We ran those specs through IntentSpec — a CLI that scores, lints, and enforces agent intent — and the gaps are consistent.

## What we measured

We analyzed **22 agent specifications** from our open-source fixture suite using `intentspec analyze tests/fixtures`:

- **2 declared `intent.yaml` specs** (fully structured intent documents)
- **20 AGENTS.md / SKILL.md files** (converted to intent via IntentSpec's parser)

Average Intent Debt Score (IDS): **~81/100** — decent documentation, but systematic blind spots.

Declared specs average **~88 IDS**. Converted markdown specs average **~81 IDS**. The delta is not about writing quality — it's about structure. Markdown files rarely encode negative constraints in a machine-checkable way.

## The surprising finding

**100% of converted AGENTS.md specs declare allowed tools but never declare forbidden tools.**

Markdown agent specs describe what an agent *can* do. They almost never document what it *must not* do at the tool level. No `denied` list. No explicit blocklist. No "this agent must never call `production_deployer`."

That's not a parser bug — it's a documentation culture gap. Teams write goals and tool lists. They don't write negative constraints in a format CI can enforce.

Other gaps in converted specs:

- **25%** have no hard non-negotiables (boundaries with `severity: hard`)
- **25%** have no enforceable constraints
- **100%** have no escalation path

Among declared `intent.yaml` specs, **50%** still lack denied tools — better, but not universal. Structured intent helps, but only if teams fill in every field.

## What a report card looks like

IntentSpec ships `intentspec report` — a shareable grade card for PRs, audits, or social posts. Here is real output from our fixture suite.

**Well-documented agent (Grade A):**

```markdown
# Agent Report Card — code-reviewer

**Grade:** A · **IDS:** ~95/100 · **Coverage:** 100%
**Type:** coding

## Strengths
- 3 hard non-negotiable(s) defined
- 3 allowed tool(s) with rationale
- Strong structural coverage (100%)
- Well-documented intent spec

## Risks
- goal-without-success-criteria: Goal 2 has no success criteria
- goal-without-success-criteria: Goal 3 has no success criteria

## Lint Summary
- Errors: 0
- Warnings: 2
```

**Typical converted spec (Grade B — missing blocklist):**

```markdown
# Agent Report Card — kubernetes-contributor-agent

**Grade:** B · **IDS:** ~81/100 · **Coverage:** 100%

## Risks
- No denied tools — agent has no explicit tool blocklist
- missing-escalation: No escalation path defined for agent failures
- missing-failure-modes: No failure modes documented
```

Terminal box format for screenshots:

```
╔══════════════════════════════════════╗
║  AGENT REPORT CARD                   ║
╠══════════════════════════════════════╣
║  code-reviewer                       ║
║  Grade: A     IDS: ~95/100           ║
║  Coverage: 100%                      ║
╚══════════════════════════════════════╝
```

Generate your own:

```bash
pip install intentspec
intentspec report path/to/intent.yaml --format markdown
intentspec report path/to/intent.yaml --format text   # for screenshots
```

## Try it without installing

Paste any `AGENTS.md` into the web demo — no pip install required:

```bash
intentspec dashboard --serve
# Open http://127.0.0.1:8080/demo
```

Paste your spec, click Analyze, get an instant grade + risk list. Under the hood it runs the same converter and linter as the CLI.

## Why this matters for CI

IntentSpec's `intentspec ci` runs validate + lint + score + coverage in one pass:

```bash
intentspec ci --min-coverage 80 --strict
```

Exit codes: **0** pass, **1** validation error, **2** warning, **3** fatal. The GitHub Action posts status checks on PRs. The point isn't documentation for documentation's sake — it's **coverage analysis for agent behavior**. You wouldn't ship code without tests. You shouldn't ship agents without declared constraints.

Inner dev loop utilities in v1.2+:

- `intentspec watch` — validate + test on save
- `intentspec test` — structural intent tests (no LLM mocking)
- `intentspec status` — quiet GitHub status check output

## Gate validation (ONI-195)

We automated Phase 2A go/no-go checks:

```bash
intentspec gate tests/ --format markdown -o ONI-195_VALIDATION.md
```

Automatable criteria: **PASS**

- MCP enforcement: **0%** false-positive rate (5 fixture servers)
- Converter accuracy: **100%** on 15 fixtures
- Framework adapters: **94%** average field extraction
- Schema migration: all v1.0 fixtures migrate cleanly

Manual criteria still pending: EU AI Act legal review, GitHub stars milestone, external lint reviewer panel.

## Get started

```bash
pip install intentspec==1.3.0
intentspec init --from agentskills   # or AGENTS.md / SKILL.md
intentspec ci --min-coverage 80
intentspec report intent.yaml --format markdown -o report-card.md
intentspec analyze . --format markdown   # aggregate stats for your repo
```

Open source (MIT): [github.com/onicarps/intentspec](https://github.com/onicarps/intentspec)

If you're building agents with CrewAI, LangGraph, AutoGen, or OpenAI Agents SDK, IntentSpec can import your framework config and generate a starter `intent.yaml` in one command. From there, every check — score, lint, coverage, report — runs against the same Intent model, not raw YAML fragments.

---

*Methodology: fixture-based analysis, June 26 2026. Sample is benchmark fixtures (22 specs), not a random sample of GitHub repos. Expanding to real-world repos next. Reproduce: `intentspec analyze tests/fixtures --format markdown`.*