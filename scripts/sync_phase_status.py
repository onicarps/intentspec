#!/usr/bin/env python3
"""Sync IntentSpec phase status to Notion page and Linear issues."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

NOTION_PAGE_ID = "380e2527-f317-8106-93f8-d93b6c9d3b17"
LINEAR_API = "https://api.linear.app/graphql"
SCRIPT_DIR = Path(__file__).resolve().parent


def _load_token(env_name: str, file_candidates: list[Path]) -> str:
    val = os.environ.get(env_name, "").strip()
    if val:
        return val
    for p in file_candidates:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{env_name}="):
                return line.split("=", 1)[1].strip()
    return ""


def notion_request(method: str, path: str, body: dict | None = None) -> dict:
    token = _load_token(
        "NOTION_API_TOKEN",
        [Path("/tmp/notion_token.txt"), SCRIPT_DIR.parent.parent / ".env", Path.home() / ".hermes" / ".env"],
    )
    if not token:
        raise RuntimeError("NOTION_API_TOKEN not found")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.notion.com/v1{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def linear_gql(query: str, variables: dict | None = None) -> dict:
    token = _load_token(
        "LINEAR_API_KEY",
        [Path("/tmp/linear_token.txt"), SCRIPT_DIR.parent / ".env", Path.home() / ".hermes" / ".env"],
    )
    if not token:
        raise RuntimeError("LINEAR_API_KEY not found")
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        LINEAR_API,
        data=json.dumps(payload).encode(),
        headers={"Authorization": token, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    if result.get("errors"):
        raise RuntimeError(json.dumps(result["errors"], indent=2))
    return result.get("data", {})


def update_notion_block(block_id: str, text: str, block_type: str = "paragraph") -> None:
    notion_request(
        "PATCH",
        f"/blocks/{block_id}",
        {block_type: {"rich_text": [{"type": "text", "text": {"content": text}}]}},
    )


def sync_notion() -> None:
    blocks = notion_request("GET", f"/blocks/{NOTION_PAGE_ID}/children?page_size=100")["results"]
    by_index = {i: b for i, b in enumerate(blocks)}

    updates: dict[int, str] = {
        15: "Phase 2A + 2B + 2C: COMPLETE ✅",
        16: "PyPI: 0.3.0 (pre-1.0) | Tests: 977 passing | Tag: v0.3.0",
        26: "Phase 2A: ONI-184, ONI-185, ONI-194, ONI-186, ONI-187, ONI-191–193, ONI-208, ONI-195 — Done",
        27: "Phase 2B: ONI-206 (test), ONI-207 (trend), ONI-132 (pre-commit), ONI-130 (GH Action) — Done",
        28: "Cut to Phase 3: ONI-209 (eval-harness), ONI-188 (EU AI Act), ONI-190 (badge), ONI-211 (agentskills export)",
        32: "Next: Phase 3 (Publish + Integrate)",
        33: "Beta program (5–10 users on real repos)",
        34: "TestPyPI gate before PyPI releases",
        35: "Real-repo analyze + content distribution",
    }

    # Append 2C bullets after block 24 if blocks 21-24 exist
    extra_2c = [
        "intentspec report (shareable grade card)",
        "Dashboard /demo (Try It Now)",
        "intentspec analyze + content marketing",
        "intentspec gate (ONI-195) + QA/packaging fixes",
    ]
    for i, text in updates.items():
        if i < len(blocks):
            btype = blocks[i].get("type", "paragraph")
            if btype in ("paragraph", "heading_2", "heading_3", "bulleted_list_item"):
                update_notion_block(blocks[i]["id"], text, btype)
                print(f"  Notion block {i}: updated")

    # Insert 2C heading + bullets if missing (after coverage trend bullet ~24)
    if len(blocks) > 24 and blocks[24].get("type") == "bulleted_list_item":
        # Check if 2C section already present
        has_2c = any(
            "report" in "".join(
                t.get("plain_text", "")
                for t in blocks[j].get("bulleted_list_item", {}).get("rich_text", [])
            )
            for j in range(17, min(26, len(blocks)))
        )
        if not has_2c:
            notion_request(
                "PATCH",
                f"/blocks/{NOTION_PAGE_ID}/children",
                {
                    "children": [
                        {
                            "object": "block",
                            "type": "heading_3",
                            "heading_3": {
                                "rich_text": [{"type": "text", "text": {"content": "Phase 2C Shipped (0.3.0)"}}]
                            },
                        },
                        *[
                            {
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [{"type": "text", "text": {"content": t}}]
                                },
                            }
                            for t in extra_2c
                        ],
                    ]
                },
            )
            print("  Notion: inserted Phase 2C section")

    print("✅ Notion page updated")


def linear_update_status(identifier: str, state_name: str) -> str:
    data = linear_gql(
        """
        query($id: String!) {
          issue(id: $id) {
            id identifier title state { name }
            team { states { nodes { id name } } }
          }
        }
        """,
        {"id": identifier},
    )
    issue = data.get("issue")
    if not issue:
        return f"{identifier}: not found"
    states = issue["team"]["states"]["nodes"]
    state_id = next((s["id"] for s in states if s["name"] == state_name), None)
    if not state_id:
        return f"{identifier}: state {state_name!r} not found"
    if issue["state"]["name"] == state_name:
        return f"{identifier}: already {state_name}"
    linear_gql(
        """
        mutation($id: String!, $stateId: String!) {
          issueUpdate(id: $id, input: { stateId: $stateId }) {
            success issue { identifier state { name } }
          }
        }
        """,
        {"id": issue["id"], "stateId": state_id},
    )
    return f"{identifier}: {issue['state']['name']} → {state_name}"


def linear_add_comment(identifier: str, body: str) -> None:
    data = linear_gql(
        'query($id: String!) { issue(id: $id) { id } }',
        {"id": identifier},
    )
    issue_id = data["issue"]["id"]
    linear_gql(
        """
        mutation($id: String!, $body: String!) {
          commentCreate(input: { issueId: $id, body: $body }) { success }
        }
        """,
        {"id": issue_id, "body": body},
    )


def sync_linear() -> None:
    done = [
        "ONI-186",  # enforce --mcp
        "ONI-187",  # lint v2
        "ONI-194",  # converter accuracy
        "ONI-195",  # gate validation
        "ONI-206",  # test framework
        "ONI-207",  # coverage trend
        "ONI-132",  # pre-commit
        "ONI-130",  # GitHub Action / status workflow
        "ONI-133",  # audit-report
        "ONI-197",  # MCP gate validation (proxy via ONI-195)
        "ONI-198",  # lint FP gate (proxy via ONI-195)
    ]
    canceled = [
        "ONI-209",  # eval-harness — cut Phase 3
        "ONI-211",  # agentskills export — cut Phase 3
    ]
    backlog_phase3 = [
        "ONI-188",  # EU AI Act — Phase 3
        "ONI-190",  # badge — Phase 3
        "ONI-213",  # PDD kill criteria — ongoing Phase 3
    ]

    print("Linear updates:")
    for ident in done:
        print(f"  {linear_update_status(ident, 'Done')}")
        time.sleep(0.3)
    for ident in canceled:
        print(f"  {linear_update_status(ident, 'Canceled')}")
        time.sleep(0.3)

    comment = (
        "Phase sync (June 26 2026): Phase 2A+2B+2C complete. "
        "PyPI 0.3.0 published (pre-1.0). 977 tests passing. "
        "See github.com/onicarps/intentspec STATUS.md."
    )
    for ident in ["ONI-206", "ONI-195", "ONI-209"]:
        try:
            linear_add_comment(ident, comment)
            print(f"  {ident}: comment added")
        except Exception as e:
            print(f"  {ident}: comment failed — {e}")
        time.sleep(0.3)

    print("✅ Linear issues updated")
    print(f"  Phase 3 backlog (unchanged): {', '.join(backlog_phase3)}")


def main() -> int:
    print("=== Notion sync ===")
    try:
        sync_notion()
    except Exception as e:
        print(f"❌ Notion failed: {e}", file=sys.stderr)
        return 1

    print("\n=== Linear sync ===")
    try:
        sync_linear()
    except Exception as e:
        print(f"❌ Linear failed: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())