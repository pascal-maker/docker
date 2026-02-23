"""A2A API security tests: agent card reachable, message/send auth policy.

Run against live A2A URL (e.g. staging after deploy). URL from A2A_URL env or
.refactor-agent-a2a-url; see tests/security/conftest.py.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Repo root for script paths (tests/security/a2a/test_*.py -> ... -> repo)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_probe_a2a_agent_card_reachable(a2a_base_url: str) -> None:
    """GET /.well-known/agent-card.json returns 200."""
    import urllib.request

    if "localhost" in a2a_base_url or "127.0.0.1" in a2a_base_url:
        pytest.skip("Security tests against live URL; set A2A_URL for staging")
    url = f"{a2a_base_url}/.well-known/agent-card.json"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
    assert "skills" in data
    assert any(s.get("id") == "refactor" for s in data.get("skills", []))


def test_a2a_message_send_requires_auth_when_required(a2a_base_url: str) -> None:
    """With --require-auth-for-send, check script exits 0 when server enforces auth."""
    if "localhost" in a2a_base_url or "127.0.0.1" in a2a_base_url:
        pytest.skip("Security tests against live URL; set A2A_URL for staging")
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / "scripts" / "check_a2a_security.py"),
            "--base-url",
            a2a_base_url,
            "--require-auth-for-send",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        timeout=30,
        check=False,
        env={"A2A_URL": a2a_base_url, **__import__("os").environ},
    )
    assert proc.returncode == 0, (
        f"check_a2a_security --require-auth-for-send failed: {proc.stderr or proc.stdout}"
    )
