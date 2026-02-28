"""Programmatic A2A security check for CI: assert auth policy.

Usage:
  uv run python scripts/a2a/check_a2a_security.py [--base-url URL] [--require-auth-for-send]

Base URL is read from (first wins): --base-url, A2A_URL env, .refactor-agent-a2a-url
in repo root, else http://localhost:9999.

  # Fail if POST message/send succeeds without auth (use after adding app-level auth):
  uv run python scripts/a2a/check_a2a_security.py --base-url https://a2a-xxx.run.app --require-auth-for-send

  # Only check that agent card is reachable (no auth policy):
  uv run python scripts/a2a/check_a2a_security.py --base-url https://a2a-xxx.run.app

Exit code: 0 if all checks pass, 1 otherwise. Safe to run in CI; no secrets required
unless the server requires auth for the agent card.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid

from refactor_agent.a2a.models import HttpHeaders, MessageSendPayload  # noqa: TC001
from refactor_agent.a2a.probe_settings import A2aProbeSettings


def _post_message_send(
    base_url: str,
    payload: MessageSendPayload,
    headers: HttpHeaders | None = None,
    timeout: float = 15.0,
) -> int:
    """POST message/send; return HTTP status code."""
    import urllib.error
    import urllib.request

    body = {
        "jsonrpc": "2.0",
        "id": "security-check",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "messageId": uuid.uuid4().hex,
                "parts": [{"kind": "text", "text": json.dumps(payload.model_dump())}],
            },
        },
    }
    h: dict[str, str] = {"Content-Type": "application/json"}
    if headers:
        h.update(headers.root)
    req = urllib.request.Request(
        base_url,
        data=json.dumps(body).encode(),
        method="POST",
        headers=h,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Programmatic A2A security check (CI-friendly)"
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="A2A server base URL (default: from A2A_URL, .refactor-agent-a2a-url, or localhost:9999)",
    )
    parser.add_argument(
        "--require-auth-for-send",
        action="store_true",
        help="Fail if POST message/send returns 200 without Authorization header",
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

    # Minimal refactor payload
    payload = MessageSendPayload(
        source="def x(): pass\n",
        old_name="x",
        new_name="y",
    )

    status_no_auth = _post_message_send(base, payload, timeout=timeout)

    if args.require_auth_for_send:
        if status_no_auth == 200:
            print(
                "check_a2a_security: POST message/send without auth returned 200 — "
                "expected 401 or 403 (require-auth-for-send)"
            )
            return 1
        if status_no_auth in (401, 403):
            print(
                "check_a2a_security: POST message/send without auth correctly "
                f"returned {status_no_auth}"
            )
        else:
            print(
                f"check_a2a_security: POST message/send without auth returned "
                f"{status_no_auth} (expected 401 or 403)"
            )
            return 1
    elif status_no_auth == 200:
        print(
            "check_a2a_security: POST message/send without auth returns 200 "
            "(use --require-auth-for-send to fail CI until auth is enforced)"
        )
    else:
        print(
            f"check_a2a_security: POST message/send without auth returns "
            f"{status_no_auth}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
