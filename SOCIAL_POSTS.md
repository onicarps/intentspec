# Social Media Launch Posts

## HN (Hacker News)

**Title:** IntentSpec – Test coverage for AI agent behavior

**Body:**
IntentSpec is a CLI tool that transforms agent development from ad-hoc documentation to versioned, testable, and enforceable intent.

Instead of scattered AGENTS.md files and tribal knowledge, you get:
- `intentspec validate` — Schema + semantic checks
- `intentspec score` — Intent Debt Score (0-100) across 7 weighted components
- `intentspec ci` — Single CI/CD hook that runs validate + lint + score + coverage
- `intentspec diff` — Git-integrated change tracking
- `intentspec health` — Terminal dashboard with coverage trends

Supports 7 input formats: AGENTS.md, SKILL.md, agentskills, CrewAI, LangGraph, AutoGen, OpenAI Agents SDK.

Open source, MIT licensed. 729 tests, 11 commands.

GitHub: https://github.com/onicarps/intentspec

## Reddit (r/LocalLLaMA, r/MachineLearning)

**Title:** [Tool] IntentSpec - Test coverage and intent scoring for AI agents

I built IntentSpec to solve a problem I kept having: how do you know if an agent's spec is complete? How do you track changes to agent intent over time? How do you enforce it in CI/CD?

It converts AGENTS.md, SKILL.md, CrewAI, LangGraph, AutoGen, and OpenAI Agents configs into a standardized intent.yaml, then gives you:

- Validation (schema + semantic checks)
- Scoring (Intent Debt Score 0-100)
- Diff tracking (git-integrated)
- Health dashboard (stale intents, coverage trends, IDS distribution)
- CI/CD integration (single command, proper exit codes)

Supports importing from 7 agent spec formats. 729 tests. MIT licensed.

https://github.com/onicarps/intentspec

## Twitter/X

🧵 IntentSpec: Test coverage for AI agent behavior

1/ AI agents are defined by scattered markdown files and tribal knowledge. IntentSpec makes that explicit and measurable.

2/ Convert any agent spec → standardized intent.yaml:
- AGENTS.md, SKILL.md, agentskills
- CrewAI, LangGraph, AutoGen
- OpenAI Agents SDK

3/ Get validation, scoring (Intent Debt Score 0-100), CI/CD integration, and drift detection.

4/ 729 tests. 11 commands. MIT licensed.

👉 https://github.com/onicarps/intentspec

## LinkedIn

**Post:**

I've been working on IntentSpec — a CLI tool that brings test coverage to AI agent behavior.

The problem: agent specs live in scattered markdown files with no standard way to validate, score, or enforce them.

The solution: IntentSpec converts any agent spec (AGENTS.md, SKILL.md, CrewAI, LangGraph, AutoGen, OpenAI Agents) into a standardized intent.yaml, then gives you:

✅ Schema + semantic validation
✅ Intent Debt Score (0-100) across 7 weighted components
✅ Git-integrated diff tracking
✅ CI/CD integration
✅ Health dashboard with coverage trends
✅ Drift detection for stale specs
✅ Compliance reporting (SOC 2 / EU AI Act)

729 tests. 11 commands. Open source (MIT).

Check it out: https://github.com/onicarps/intentspec
