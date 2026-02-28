"""Cloud Function: Firestore trigger to email admin on new pending user.

Triggered on document create in users collection when status is 'pending'.
Sends email via Resend to admin.
Uses functions_framework for Cloud Functions Gen2 (Terraform deployment).
"""

from __future__ import annotations

import json
import os
import urllib.request

import functions_framework


def _parse_firestore_value(value: dict) -> str | int | float | bool | None:  # noqa: no-dict-sig  # Firestore Value
    """Extract scalar from Firestore Value message."""
    parsers: dict[str, object] = {
        "stringValue": lambda: value["stringValue"],
        "integerValue": lambda: int(value["integerValue"]),
        "doubleValue": lambda: float(value["doubleValue"]),
        "booleanValue": lambda: value["booleanValue"],
        "nullValue": lambda: None,
    }
    for key, parser in parsers.items():
        if key in value:
            return parser()  # type: ignore[return-value]
    return None


def _parse_firestore_document(data: dict) -> dict:  # noqa: no-dict-sig  # Firestore CloudEvent payload
    """Parse Firestore Document from CloudEvent data.value."""
    value = data.get("value") or {}
    fields = value.get("fields") or {}
    result: dict[str, str | int | float | bool | None] = {}
    for key, val in fields.items():
        result[key] = _parse_firestore_value(val)
    return result


def _send_admin_notification(
    admin_email: str,
    api_key: str,
    github_login: str,
    user_email: str,
) -> None:
    """Send email to admin via Resend API."""
    from_addr = os.environ.get("FROM_EMAIL", "Refactor Agent <onboarding@resend.dev>")
    payload = {
        "from": from_addr,
        "to": [admin_email],
        "subject": f"Refactor Agent: Access request from {github_login}",
        "html": (
            f"<p>A new user has requested access to Refactor Agent.</p>"
            f"<p><strong>GitHub:</strong> {github_login}</p>"
            f"<p><strong>Email:</strong> {user_email or 'not provided'}</p>"
            f"<p>Approve via Firestore console or <code>scripts/auth/approve_user.py</code>.</p>"
        ),
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "refactor-agent-email-notify/1.0",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


@functions_framework.cloud_event
def on_user_created(cloud_event) -> None:
    """Send email to admin when a new user with status=pending is created."""
    admin_email = os.environ.get("ADMIN_EMAIL")
    api_key = os.environ.get("RESEND_API_KEY")
    if not admin_email or not api_key:
        return
    data = cloud_event.data or {}
    doc_data = _parse_firestore_document(data)
    if doc_data.get("status") != "pending":
        return
    login = str(doc_data.get("github_login", "unknown"))
    user_email = str(doc_data.get("email", "")) if doc_data.get("email") else ""
    _send_admin_notification(admin_email, api_key, login, user_email)
