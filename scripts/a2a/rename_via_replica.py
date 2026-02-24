"""Call A2A agent with use_replica to rename a symbol, then apply artifacts locally."""

from __future__ import annotations

import json
import sys
import time
import uuid

import httpx

DEFAULT_BASE = "http://localhost:9999"
SEND_TIMEOUT = 120.0  # use_replica scans whole replica (can be slow)
GET_TIMEOUT = 30.0


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE).rstrip("/")
    task_id = str(uuid.uuid4())
    payload = {"old_name": "greet", "new_name": "greet_user", "use_replica": True}

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
    print("Sending rename (use_replica)... may take a while if replica is large.")
    with httpx.Client(timeout=SEND_TIMEOUT) as client:
        r = client.post(base, json=body)
        r.raise_for_status()
        out = r.json()
    if "error" in out:
        print("Send error:", out["error"])
        sys.exit(1)
    print("Sent task_id=", task_id)

    # Poll for result
    get_body = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "tasks/get",
        "params": {"id": task_id},
    }
    for _ in range(10):
        with httpx.Client(timeout=GET_TIMEOUT) as client:
            r2 = client.post(base, json=get_body)
            r2.raise_for_status()
            data = r2.json()
        if "error" in data:
            print("Get error:", data["error"])
            sys.exit(1)
        task = data.get("result")
        state = (task.get("status") or {}).get("state") if task else None
        if state in ("completed", "failed"):
            break
        time.sleep(1)

    artifacts = (task or {}).get("artifacts") or []
    applied = 0
    for a in artifacts:
        for part in a.get("parts") or []:
            if part.get("type") == "data" or part.get("kind") == "data":
                d = part.get("data") or {}
                path = d.get("path")
                mod = d.get("modified_source")
                if path and mod is not None:
                    # Path from replica is e.g. python/greeter.py
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(mod)
                    print("Applied to", path)
                    applied += 1
    if applied:
        print("Done. Renamed in", applied, "file(s).")
    else:
        print("No artifacts to apply. Status:", state)
        msg = (task or {}).get("status") or {}
        if isinstance(msg.get("message"), dict):
            for p in msg["message"].get("parts") or []:
                if p.get("type") == "text" or p.get("kind") == "text":
                    print(p.get("text", "")[:500])
                    break


if __name__ == "__main__":
    main()
