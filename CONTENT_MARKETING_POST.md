# We Analyzed 22 Agent Specs. Most Never Say What Tools Are Forbidden.

*Coverage analysis for agent behavior — not another prompt framework.*

When you ship an AI agent, how do you know it won't do something you never intended? Most teams answer with a markdown file: `AGENTS.md`, `SKILL.md`, or a framework config. We ran those specs through IntentSpec — a CLI that scores, lints, and enforces agent intent — and the gaps are consistent.

## What we measured

We analyzed **22 agent specifications** from our open-source fixture suite:

- **2 declared `intent.yaml` specs** (fully structured intent documents)
- **20 AGENTS.md / SKILL.md files** (converted to intent via IntentSpec's parser)

Average Intent Debt Score (IDS): **~81/100** — decent documentation, but systematic blind spots.

## The surprising finding

**100% of converted AGENTS.md specs declare allowed tools but never declare forbidden tools.**

Markdown agent specs describe what an agent *can* do. They almost never document what it *must not* do at the tool level. No `denied` list. No explicit blocklist. No "this agent must never call `production_deployer`."

That's not a parser bug — it's a documentation culture gap. Teams write goals and tool lists. They don't write negative constraints in a machine-checkable format.

Other gaps in converted specs:

- **25%** have no hard non-negotiables (boundaries with `severity: hard`)
- **25%** have no enforceable constraints
- **100%** have no escalation path

Declared `intent.yaml` specs score higher (~88 IDS avg) and include denied tools — but they're rare. Most teams haven't adopted structured intent yet.

## What a report card looks like

IntentSpec now ships `intentspec report` — a shareable grade card you can paste into PRs or social posts:

```
╔══════════════════════════════════════╗
║  AGENT REPORT CARD                   ║
╠══════════════════════════════════════╣
║  code-reviewer                       ║
║  Grade: A     IDS: ~95/100           ║
║  Coverage: 100%                      ║
╚══════════════════════════════════════╝
```

Run it yourself:

```bash
pip install intentspec
intentspec report path/to/intent.yaml --format markdown
```

## Try it without installing

Paste any `AGENTS.md` into the web demo:

```bash
intentspec dashboard --serve
# Open http://127.0.0.1:8080/demo
```

You get an instant grade, IDS estimate, and risk list — no pip install required for the demo.

## Why this matters for CI

IntentSpec's `intentspec ci` command runs validate + lint + score + coverage in one pass with proper exit codes (0 pass, 1 error, 2 warning, 3 fatal). The GitHub Action posts status checks on PRs.

The point isn't documentation for documentation's sake. It's **coverage analysis for agent behavior** — the same way you wouldn't ship code without tests, you shouldn't ship agents without declared constraints.

## Gate validation (ONI-195)

We also automated Phase 2A gate checks:

```bash
intentspec gate tests/ --format markdown -o ONI-195_VALIDATION.md
```

Automatable criteria: **PASS** — MCP enforcement 0% false-positive rate on fixture servers, converter 100% accuracy on 15 fixtures, framework adapters 94% average field extraction.

## Get started

```bash
pip install intentspec==1.2.0
intentspec init --from agentskills   # or AGENTS.md
intentspec ci --min-coverage 80
intentspec report intent.yaml --format markdown -o report-card.md
```

Open source (MIT): [github.com/onicarps/intentspec](https://github.com/onicarps/intentspec)

---

*Methodology: fixture-based analysis, June 26 2026. Sample is benchmark fixtures, not a random sample of GitHub repos. We're expanding to real-world repos next.*