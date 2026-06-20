#!/usr/bin/env python3
"""Get IntentSpec page content from Notion."""
import urllib.request, json, os

token = os.environ.get("NOTION_API_TOKEN", "")

# Search for the page ID
req = urllib.request.Request(
    "https://api.notion.com/v1/search",
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    },
    data=json.dumps({"query": "IntentSpec"}).encode()
)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read())

page_id = data["results"][0]["id"]
print(f"Page ID: {page_id}")

# Get page content
req2 = urllib.request.Request(
    f"https://api.notion.com/v1/pages/{page_id}",
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
)
with urllib.request.urlopen(req2, timeout=10) as resp:
    page = json.loads(resp.read())

print(f"Page URL: {page.get('url', '?')}")
print(f"Properties: {list(page.get('properties', {}).keys())}")

# Get page blocks (content)
req3 = urllib.request.Request(
    f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100",
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
)
with urllib.request.urlopen(req3, timeout=10) as resp:
    blocks = json.loads(resp.read())

print(f"\nBlocks ({len(blocks.get('results', []))}):")
for b in blocks.get("results", [])[:20]:
    btype = b.get("type", "?")
    if btype in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item", "to_do", "toggle", "divider"):
        texts = b.get(btype, {}).get("rich_text", [])
        content = "".join(t.get("plain_text", "") for t in texts)
        if content:
            print(f"  [{btype}] {content[:100]}")
    elif btype == "child_database":
        title = b.get("child_database", {}).get("title", "?")
        print(f"  [database] {title}")
    elif btype != "unsupported":
        print(f"  [{btype}]")

# Check for child databases
print("\n--- Child Databases ---")
for b in blocks.get("results", []):
    if b.get("type") == "child_database":
        db_id = b["id"]
        title = b.get("child_database", {}).get("title", "?")
        print(f"DB: {title} ({db_id})")
        # Get database schema
        req4 = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{db_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28"
            }
        )
        try:
            with urllib.request.urlopen(req4, timeout=10) as resp:
                db = json.loads(resp.read())
            print(f"  Properties: {list(db.get('properties', {}).keys())}")
        except Exception as e:
            print(f"  Error: {e}")
