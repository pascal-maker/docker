"""Test the A2A server human-in-the-loop (name collision) flow.

Run the A2A server first in another terminal:
  uv run python scripts/a2a/run_ast_refactor_a2a.py

Then run this script:
  uv run python scripts/a2a/test_a2a_collision.py [BASE_URL]

Step 1: Sends a rename that causes a collision (greet -> main when main exists).
Step 2: If the response is input_required, sends "yes" to confirm (or pass --no to cancel).

If you see "Renamed..." in Step 1 instead of "Response kind: task" and "input-required",
restart the A2A server so it loads the executor with collision detection.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import uuid
from typing import TYPE_CHECKING

from refactor_agent.a2a.models import JsonRpcResponse

if TYPE_CHECKING:
    import types

_urllib_request: types.ModuleType | None = None
with contextlib.suppress(ImportError):
    import urllib.request

    _urllib_request = urllib.request


def send_message(
    base_url: str,
    text: str,
    *,
    context_id: str | None = None,
    task_id: str | None = None,
) -> JsonRpcResponse:
    """POST message/send and return the parsed JSON response."""
    if _urllib_request is None:
        sys.exit("Need urllib (standard library)")
    message: dict = {
        "kind": "message",
        "role": "user",
        "messageId": uuid.uuid4().hex,
        "parts": [{"kind": "text", "text": text}],
    }
    if context_id is not None:
        message["contextId"] = context_id
    if task_id is not None:
        message["taskId"] = task_id
    body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {"message": message},
    }
    data = json.dumps(body).encode("utf-8")
    req = _urllib_request.Request(
        base_url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with _urllib_request.urlopen(req, timeout=10) as resp:
        return JsonRpcResponse.model_validate(json.loads(resp.read().decode()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Test A2A name-collision flow")
    parser.add_argument(
        "base_url",
        nargs="?",
        default="http://localhost:9999",
        help="A2A server base URL",
    )
    parser.add_argument(
        "--no",
        action="store_true",
        help="On resumption, send 'no' to cancel instead of 'yes'",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    # Step 1: send collision-producing rename
    task_payload = {
        "source": "def main(): pass\n\ndef greet(n): return n\n",
        "old_name": "greet",
        "new_name": "main",
    }
    print("Step 1: Sending rename greet -> main (main already exists)...")
    result = send_message(base_url, json.dumps(task_payload))

    if "error" in result.root:
        print("Error:", json.dumps(result.root, indent=2))
        return 1

    res = result.root.get("result") or {}
    kind = res.get("kind", "")
    task_status = res.get("status") or {}
    state = (task_status or {}).get("state", "")

    print("Response kind:", kind)
    print("Status state:", state or "(none)")

    if kind == "task":
        task_id = res.get("id")
        context_id = res.get("contextId")
        print("Task ID:", task_id)
        print("Context ID:", context_id)
        if state == "input-required":
            print("Artifacts:", len(res.get("artifacts") or []))
            confirm = "no" if args.no else "yes"
            print(f"\nStep 2: Sending '{confirm}' to confirm/cancel...")
            result2 = send_message(
                base_url, confirm, context_id=context_id, task_id=task_id
            )
            if "error" in result2.root:
                print("Error:", json.dumps(result2.root, indent=2))
                return 1
            res2 = result2.root.get("result") or {}
            parts = (res2.get("parts") or []) if isinstance(res2, dict) else []
            for p in parts:
                if isinstance(p, dict) and "text" in p:
                    print(
                        "Result:",
                        p["text"][:200] + ("..." if len(p["text"]) > 200 else ""),
                    )
                    break
            else:
                print("Result:", json.dumps(result2.root, indent=2)[:500])
        else:
            print("Full result:", json.dumps(result.root, indent=2)[:800])
    else:
        # Message response (no collision triggered?)
        parts = res.get("parts") or []
        for p in parts:
            if isinstance(p, dict) and "text" in p:
                print("Agent message:", p["text"][:300])
                break
        else:
            print("Full result:", json.dumps(result.root, indent=2)[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
