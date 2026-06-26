# Social Posts v2 — Data-Led (June 26 2026)

Based on `CONTENT_ANALYSIS.md` (22 specs, fixture suite).

---

## Hacker News

**Title:** IntentSpec – We analyzed 22 agent specs; none declare forbidden tools

**Body:**

I built IntentSpec (MIT, `pip install intentspec`) — coverage analysis and CI enforcement for AI agent specs.

Ran 22 agent specs (AGENTS.md, SKILL.md, intent.yaml) through our parser and scorer. Findings:

- 100% of converted AGENTS.md specs list allowed tools but **zero** declare denied/forbidden tools
- 25% have no hard non-negotiables
- Avg IDS score ~81/100 — decent docs, systematic blind spots

New in v1.2.0:
- `intentspec report` — shareable agent grade card
- Web demo: paste AGENTS.md → instant risk report (no install)
- `intentspec gate` — automated validation gate checks

```bash
pip install intentspec
intentspec report intent.yaml --format markdown
intentspec dashboard --serve  # /demo for paste-and-analyze
```

GitHub: https://github.com/onicarps/intentspec

Happy to answer questions on the methodology — fixture-based for now, expanding to real repos.

---

## Reddit r/MachineLearning

**Title:** [Tool] IntentSpec v1.2 — analyzed 22 agent specs, 100% missing tool blocklists

**Body:**

IntentSpec documents agent behavior as code (`intent.yaml`), scores coverage, and enforces through CI.

**Data from our fixture analysis (22 specs):**
- Converted AGENTS.md files: 100% declare allowed tools, 0% declare denied tools
- 25% lack hard non-negotiables
- Declared intent.yaml specs score ~88 IDS vs ~81 for markdown

**v1.2.0 commands:**
| Command | What it does |
|---------|-------------|
| `report` | Shareable grade card (A-F, IDS, risks) |
| `gate` | Phase 2A validation gate (ONI-195) |
| `analyze` | Aggregate spec statistics |
| `dashboard /demo` | Paste AGENTS.md, get instant analysis |

```bash
pip install intentspec
intentspec init --from agentskills
intentspec ci --min-coverage 80
```

Open source, MIT: https://github.com/onicarps/intentspec

---

## Twitter/X Thread

**1/7** We analyzed 22 AI agent specs (AGENTS.md, SKILL.md, intent.yaml). The gap is consistent: everyone documents what agents *can* do. Almost nobody documents what they *must not* do.

**2/7** 100% of converted AGENTS.md specs in our sample declare allowed tools. 0% declare forbidden tools. No blocklist. No `denied: [production_deployer]`.

**3/7** 25% have no hard non-negotiables. 25% have no enforceable constraints. Avg IDS ~81/100 — good intentions, weak guardrails.

**4/7** IntentSpec v1.2.0 ships `intentspec report` — a shareable agent grade card. Grade A-F, IDS score, risk list. Paste into PRs or posts.

**5/7** Zero-install demo: `intentspec dashboard --serve` → `/demo` → paste your AGENTS.md → instant grade + risks. No pip required for the demo.

**6/7** CI enforcement: `intentspec ci` runs validate + lint + score + coverage. GitHub Action posts PR status checks. Exit codes: 0 pass, 1 error, 2 warning, 3 fatal.

**7/7** Open source (MIT). `pip install intentspec` → github.com/onicarps/intentspec