#!/usr/bin/env python3
"""Update Notion IntentSpec page via API."""
import urllib.request, json, os

page_id = "380e2527-f317-8106-93f8-d93b6c9d3b17"
token = os.environ.get("NOTION_API_TOKEN", "")

# Use update_content with search/replace
body = {
    "type": "update_content",
    "update_content": {
        "content_updates": [
            {
                "old_str": "Current Status (June 2026)\n## Current Status\nWeeks 1-5: COMPLETE ✅  \\\\|  Week 6: IN PROGRESS 🔄\nTests: 466 passing  •  Coverage: 84%  •  Commits: 22 on main\nPhase 2 Gate: 7/8 criteria met. Gap: coverage 84% vs 88% target\n---\n### Linear Issues\nONI-156 to ONI-165 — 10 issues tracking W1-W10 milestones\nProject: IntentSpec (ONI team)\n---\n### GitHub Issues\n#1-#10 created (labels/milestones need classic PAT to create)\nRepo: https://github.com/onicarps/intentspec",
                "new_str": "Current Status — June 26 2026\n## Current Status\nPhase 2A + 2B + 2C: COMPLETE ✅\nPyPI: v1.3.1 | Tests: 977 passing | Tag: v1.3.1\n\n### Phase 2A Shipped (v1.1)\n- Schema migration, lint v2 (16 rules), MCP enforce, framework adapters\n\n### Phase 2B Shipped (v1.2)\n- intentspec test (structural testing)\n- intentspec watch + init --pre-commit\n- intentspec status + GitHub workflow\n- intentspec coverage --trend\n\n### Phase 2C Shipped (v1.3.0 → v1.3.1)\n- intentspec report (shareable grade card)\n- Dashboard /demo (Try It Now)\n- intentspec analyze + content marketing\n- intentspec gate (ONI-195 validation)\n- v1.3.1 QA fixes (templates, gate data, formats, exit codes)\n\n### Cut to Phase 3\nONI-200 (eval-harness), ONI-187 (EU AI Act), badge, agentskills export\n\n### GitHub\nRepo: https://github.com/onicarps/intentspec | Branch: main\n\n### Next: Phase 3 (Publish + Integrate)\n- Beta program (5-10 users)\n- TestPyPI gate\n- Real-repo analyze / content distribution"
            }
        ]
    }
}

data = json.dumps(body).encode()
req = urllib.request.Request(
    f"https://api.notion.com/v1/pages/{page_id}/markdown",
    data=data,
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    },
    method="PATCH"
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
        if result.get("object") == "page":
            print("✅ Notion page updated successfully")
        else:
            print(f"Response: {json.dumps(result)[:300]}")
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print(f"HTTP {e.code}: {error_body[:300]}")
