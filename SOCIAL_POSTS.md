# Social Media Launch Posts — v2 (Post-Audit)

## HN (Hacker News)

**Title:** Show HN: IntentSpec — Measure and enforce AI agent intent in CI/CD

**Body:**

I kept losing track of what my agents were supposed to do after the 3rd rewrite. AGENTS.md files drifting out of sync with code, no way to score spec quality, no CI enforcement.

IntentSpec is my attempt to fix that. It converts any agent spec format into a standardized intent.yaml, then validates, scores, and enforces it.

Key features:
- `intentspec validate` — Schema + semantic checks
- `intentspec score` — Intent Debt Score (0-100, higher = better documented)
- `intentspec ci` — Single CI/CD hook (validate + lint + score + coverage)
- `intentspec diff` — Git-integrated intent change tracking
- `intentspec drift` — Flags specs not updated in 30+ days
- `intentspec audit-report` — SOC 2 / EU AI Act compliance reports

Supports 7 input formats: AGENTS.md, SKILL.md, agentskills, CrewAI, LangGraph, AutoGen, OpenAI Agents SDK.

Open source, MIT licensed. 794 tests, 11 commands.

GitHub: https://github.com/onicarps/intentspec

How are you currently tracking agent intent changes across your team?

## Reddit (r/LocalLLaMA)

**Title:** [Tool] IntentSpec — Score and enforce AI agent specs for local LLM setups

I built IntentSpec to solve a problem I kept having: how do you know if an agent's spec is complete? How do you track changes to agent intent over time?

Especially with local LLM setups where I'm iterating fast on agent prompts and tools, the AGENTS.md files kept drifting out of sync with what the agent actually does.

It converts AGENTS.md, SKILL.md, CrewAI, LangGraph, AutoGen, and OpenAI Agents configs into a standardized intent.yaml, then gives you:

- Validation (schema + semantic checks)
- Scoring (Intent Debt Score 0-100)
- Diff tracking (git-integrated)
- Drift detection (flags stale specs)
- CI/CD integration (single command, proper exit codes)

Current limitations: converter works best with well-structured specs. LLM-based extraction is opt-in and still experimental.

Supports 7 agent spec formats. 794 tests. MIT licensed.

https://github.com/onicarps/intentspec

## Reddit (r/AIEngineering)

**Title:** [Tool] IntentSpec — CI/CD enforcement for AI agent specifications

I built IntentSpec after watching a team deploy an agent that did the wrong thing — not because the code was broken, but because the spec was 3 versions behind.

It converts any agent spec format (AGENTS.md, SKILL.md, CrewAI, LangGraph, AutoGen, OpenAI Agents) into a standardized intent.yaml, then gives you:

- Schema + semantic validation
- Intent Debt Score (0-100) across 7 weighted components
- Git-integrated diff tracking
- CI/CD gate with proper exit codes (0/1/2/3)
- Drift detection for specs not updated in 30+ days
- Compliance reporting (SOC 2 / EU AI Act)

794 tests. MIT licensed. Python 3.11+.

https://github.com/onicarps/intentspec

## Twitter/X

🧵 IntentSpec: Your AI agent's spec is probably wrong right now.

Not because you wrote it badly — because it's been 2 weeks and the code moved on.

IntentSpec fixes this. 🧵

1/ Converts any agent spec → standardized intent.yaml:
AGENTS.md, SKILL.md, agentskills, CrewAI, LangGraph, AutoGen, OpenAI Agents SDK

2/ Get a quality score:
Intent Debt Score (0-100) measures spec completeness across 7 dimensions

3/ Enforce in CI/CD:
One command. Proper exit codes. Fails builds when intent is broken.

4/ Track drift:
Flags AGENTS.md files that haven't been updated in 30+ days

5/ Open source (MIT). 794 tests. Python 3.11+.

👉 https://github.com/onicarps/intentspec

What's your biggest pain with agent specs? RT if you've been bitten by stale AGENTS.md files.

## LinkedIn

**Post:**

AI agents are going into production faster than we can audit them.

When SOC 2 reviewers ask "how do you know what your agent is supposed to do?" — most teams have no answer. Agent specs live in scattered markdown files with no validation, scoring, or enforcement.

I built IntentSpec to fix this. It converts any agent spec format (AGENTS.md, SKILL.md, CrewAI, LangGraph, AutoGen, OpenAI Agents) into a standardized intent.yaml, then gives you:

✅ Schema + semantic validation
✅ Intent Debt Score (0-100) tracking spec quality over time
✅ Git-integrated diff tracking
✅ CI/CD integration with proper exit codes
✅ Drift detection for stale specs
✅ Compliance reporting for SOC 2 and EU AI Act

794 tests. 11 commands. Open source (MIT).

If you're building AI agents in production or preparing for compliance audits, take a look:

👉 https://github.com/onicarps/intentspec

How is your team currently tracking agent intent? I'd love to hear what's working (and what's not).

#AIEngineering #DevTools #OpenSource #AIAgents #SOC2
