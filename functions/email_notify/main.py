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
from models import (
    FirestoreCloudEventData,
    ParsedUserDocument,
    parse_firestore_value,
)
from pydantic import ValidationError


def _parse_firestore_document(data: FirestoreCloudEventData) -> ParsedUserDocument:
    """Parse Firestore Document from CloudEvent data.value."""
    fields = data.value.fields
    result: dict[str, str | int | float | bool | None] = {}
    for key, val in fields.items():
        parsed = parse_firestore_value(val)
        if isinstance(parsed, (str, int, float, bool)) or parsed is None:
            result[key] = parsed

    def _str_or_none(val: str | int | float | bool | None) -> str | None:
        return str(val) if val is not None else None

    return ParsedUserDocument(
        status=_str_or_none(result.get("status")),
        github_login=_str_or_none(result.get("github_login")),
        email=_str_or_none(result.get("email")),
    )


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
    raw_data = cloud_event.data or {}
    try:
        event_data = FirestoreCloudEventData.model_validate(raw_data)
    except ValidationError:
        return
    doc_data = _parse_firestore_document(event_data)
    if doc_data.status != "pending":
        return
    login = doc_data.github_login or "unknown"
    user_email = doc_data.email or ""
    _send_admin_notification(admin_email, api_key, login, user_email)
