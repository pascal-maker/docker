"""Call the A2A agent directly (bridge-style) for quick development.

Sends tasks/send with params.id (like GongRzhe A2A-MCP-Server), then
get_task_result with that id. Run the server first:

  uv run python scripts/a2a/run_ast_refactor_a2a.py

Then:

  uv run python scripts/a2a/call_a2a_agent.py [BASE_URL]

Example with greeter source:
  uv run python scripts/a2a/call_a2a_agent.py
"""

from __future__ import annotations

import json
import sys
import uuid

import httpx

DEFAULT_BASE = "http://localhost:9999"


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE).rstrip("/")
    task_id = str(uuid.uuid4())

    # Bridge sends tasks/send with params.id and params.message
    doc = '"""Defines greet(); used by caller and extra. Rename greet → greet_user."""'
    payload = {
        "source": (
            f"{doc}\n\n"
            "from __future__ import annotations\n\n\n"
            "def greet(name: str) -> str:\n"
            '    """Return a greeting for the given name."""\n'
            '    return f"Hello, {name}!"\n'
        ),
        "old_name": "greet",
        "new_name": "greet_by_name",
    }

    body = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "tasks/send",
        "params": {
            "id": task_id,
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": json.dumps(payload)}],
            },
        },
    }

    print(f"Send task_id={task_id}")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(base, json=body)
        r.raise_for_status()
        out = r.json()

    if "error" in out:
        print("send error:", out["error"])
        sys.exit(1)

    result = out.get("result")
    if isinstance(result, dict):
        rid = result.get("id")
        st = result.get("status")
        state = st.get("state") if isinstance(st, dict) else None
        print(f"  result.id={rid} status.state={state}")
    else:
        print("  result:", result)

    print("\nGet task result...")
    get_body = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "tasks/get",
        "params": {"id": task_id},
    }
    with httpx.Client(timeout=10.0) as client:
        r2 = client.post(base, json=get_body)
        r2.raise_for_status()
        out2 = r2.json()

    if "error" in out2:
        print("get_task error:", out2["error"])
        sys.exit(1)

    task = out2.get("result")
    if isinstance(task, dict):
        st = task.get("status")
        msg = st.get("message") if isinstance(st, dict) else None
        parts = (msg.get("parts") or []) if isinstance(msg, dict) else []
        for p in parts:
            if p.get("type") == "text" or p.get("kind") == "text":
                print(p.get("text", "")[:500])
                break
    else:
        print("task:", task)
    print("OK")


if __name__ == "__main__":
    main()
