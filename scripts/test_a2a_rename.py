"""Test the A2A server: GET agent card, POST a rename task, print result.

Run the A2A server first in another terminal:
  uv run python scripts/run_ast_refactor_a2a.py

Then run this script:
  uv run python scripts/test_a2a_rename.py [BASE_URL]

Default BASE_URL is http://localhost:9999.
"""

from __future__ import annotations

import json
import sys
import uuid

def main() -> None:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9999").rstrip("/")

    try:
        import urllib.request
    except ImportError:
        # Fallback if run in odd env
        sys.exit("Need urllib (standard library)")

    # 1. GET agent card
    req = urllib.request.Request(
        f"{base_url}/.well-known/agent-card.json",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        card = json.loads(resp.read().decode())
    print("Agent card:")
    print(f"  name: {card.get('name')}")
    print(f"  url: {card.get('url')}")
    print(f"  skills: {[s.get('id') for s in card.get('skills', [])]}")

    # 2. POST message/send (A2A JSON-RPC)
    task_payload = {
        "source": "def calculate_tax(amount, rate):\n    return amount * rate\n",
        "old_name": "calculate_tax",
        "new_name": "compute_tax",
    }
    body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "messageId": uuid.uuid4().hex,
                "parts": [{"kind": "text", "text": json.dumps(task_payload)}],
            },
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        base_url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())

    print("\nmessage/send response:")
    if "result" in result:
        msg = result["result"]
        if isinstance(msg, dict):
            parts = msg.get("parts") or []
            for part in parts:
                if isinstance(part, dict) and "text" in part:
                    print(part["text"])
                    break
            else:
                print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))
    elif "error" in result:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
