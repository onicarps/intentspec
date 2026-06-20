#!/usr/bin/env python3
"""Update Notion IntentSpec page with current status."""
import urllib.request, json, subprocess

token = subprocess.run(["bash", "-c", "echo $NOTION_API_TOKEN"], capture_output=True, text=True).stdout.strip()
page_id = "380e2527-f317-8106-93f8-d93b6c9d3b17"

# Get page to verify access
req = urllib.request.Request(
    f"https://api.notion.com/v1/pages/{page_id}",
    headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
)
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        page = json.loads(resp.read())
    print("Page access OK:", page.get("url", "?"))
except Exception as e:
    print(f"Page access error: {e}")
    exit(1)

# Build children blocks
children = [
    {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Current Status"}}]}
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Weeks 1-5: COMPLETE | Week 6: IN PROGRESS"}}]}
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Tests: 466 passing | Coverage: 84% | Commits: 22 on main"}}}
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Phase 2 Gate: 7/8 criteria met. Gap: need 88% coverage (currently 84%)"}}}
    },
    {
        "object": "block",
        "type": "divider",
        "divider": {}
    },
    {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": "Linear Issues"}}}
    },
    {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": "ONI-156 to ONI-165 tracking all milestones W1-W10"}}}
    }
]

update_data = {"children": children}

req2 = urllib.request.Request(
    f"https://api.notion.com/v1/pages/{page_id}",
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    },
    data=json.dumps(update_data).encode()
)
try:
    with urllib.request.urlopen(req2, timeout=10) as resp:
        result = json.loads(resp.read())
    print("Notion update OK")
except Exception as e:
    print(f"Notion update error: {e}")
