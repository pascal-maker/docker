"""Probe A2A staging (or any base URL): what is reachable with and without auth.

Usage:
  uv run python scripts/a2a/probe_a2a.py [BASE_URL]
  uv run python scripts/a2a/probe_a2a.py https://a2a-server-xxxxx-ew.a.run.app

Base URL is read from (first wins): CLI arg, A2A_URL env, .refactor-agent-a2a-url
in repo root (from make infra-a2a-url), else http://localhost:9999.

Probes:
  - GET /.well-known/agent-card.json (no auth) — expect 200.
  - GET / (no auth) — expect 405 Method Not Allowed or 404.
  - POST / with message/send (no auth) — report status; if 200 with result,
    the task ran without auth (vulnerability if only agent-card should be public).

Optional:
  --api-key KEY  Also send Authorization: Bearer KEY on POST; report if behavior differs.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid

from refactor_agent.a2a.probe_settings import A2aProbeSettings


def _request(
    url: str,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> tuple[int, bytes, dict[str, str]]:
    """Perform HTTP request; return (status_code, body_bytes, response_headers)."""
    import urllib.error
    import urllib.request

    h = dict(headers) if headers else {}
    if data and "Content-Type" not in h:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (resp.status, resp.read(), dict(resp.headers))
    except urllib.error.HTTPError as e:
        return (e.code, e.read() if e.fp else b"", dict(e.headers) if e.headers else {})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe A2A endpoint: what is accessible with/without auth"
    )
    parser.add_argument(
        "base_url",
        nargs="?",
        default=None,
        help="A2A server base URL (default: from A2A_URL, .refactor-agent-a2a-url, or localhost:9999)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Optional API key; send Authorization: Bearer for POST when set",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Request timeout in seconds (default from settings)",
    )
    args = parser.parse_args()
    settings = A2aProbeSettings()
    base = (args.base_url or settings.a2a_url).rstrip("/")
    timeout = args.timeout if args.timeout is not None else settings.timeout
    api_key = args.api_key or settings.api_key

    issues: list[str] = []

    # 1. GET agent card (no auth) — should succeed
    url_card = f"{base}/.well-known/agent-card.json"
    status_card, body_card, _ = _request(url_card, timeout=timeout)
    if status_card == 200:
        try:
            card = json.loads(body_card.decode())
            name = card.get("name", "?")
            skills = [s.get("id") for s in card.get("skills", [])]
            print(
                f"GET /.well-known/agent-card.json (no auth): {status_card} — OK "
                f"({name}, skills={skills})"
            )
        except json.JSONDecodeError:
            print(
                f"GET /.well-known/agent-card.json (no auth): {status_card} — OK "
                "(body not JSON)"
            )
    else:
        print(f"GET /.well-known/agent-card.json (no auth): {status_card}")
        issues.append(f"Agent card returned {status_card} (expected 200)")

    # 2. GET / — should be 405 or 404 (no GET on RPC endpoint)
    status_get, _, _ = _request(base, timeout=timeout)
    if status_get in (404, 405):
        print(f"GET / (no auth): {status_get} — expected (no GET handler)")
    else:
        print(f"GET / (no auth): {status_get}")

    # 3. POST message/send without auth
    task_payload = {
        "source": "def foo(): pass\n",
        "old_name": "foo",
        "new_name": "bar",
    }
    body_rpc = {
        "jsonrpc": "2.0",
        "id": "probe-1",
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
    post_headers: dict[str, str] = {}
    if api_key:
        post_headers["Authorization"] = f"Bearer {api_key}"
    status_post, body_post, _ = _request(
        base,
        method="POST",
        data=json.dumps(body_rpc).encode(),
        headers=post_headers,
        timeout=timeout,
    )
    auth_note = " (with API key)" if api_key else " (no auth)"
    if status_post == 200:
        try:
            result = json.loads(body_post.decode())
            has_result = "result" in result and result.get("result") is not None
            has_error = "error" in result
            if has_result and not has_error:
                res = result.get("result") or {}
                looks_like_task = "id" in res or "status" in res or "parts" in res
                if looks_like_task:
                    print(
                        f"POST / message/send{auth_note}: {status_post} — "
                        "TASK RAN (no auth required)"
                    )
                    if not api_key:
                        issues.append(
                            "POST message/send accepted without auth — "
                            "only agent-card should be public"
                        )
                else:
                    print(
                        f"POST / message/send{auth_note}: {status_post} — "
                        "200 (unexpected shape)"
                    )
            elif has_error:
                print(
                    f"POST / message/send{auth_note}: {status_post} — "
                    "JSON-RPC error (no task run)"
                )
            else:
                print(
                    f"POST / message/send{auth_note}: {status_post} — 200 (no result)"
                )
        except json.JSONDecodeError:
            print(f"POST / message/send{auth_note}: {status_post} — body not JSON")
    elif status_post in (401, 403):
        print(f"POST / message/send{auth_note}: {status_post} — auth required (good)")
    else:
        print(f"POST / message/send{auth_note}: {status_post}")

    if issues:
        print("\n---")
        for i in issues:
            print("⚠", i)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
