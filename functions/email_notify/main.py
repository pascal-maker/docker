"""Cloud Function: Firestore trigger to email admin on new pending user.

Triggered on document create in users collection when status is 'pending'.
Sends email via Resend to admin.
"""

from __future__ import annotations

import json
import os
import urllib.request

from firebase_functions import firestore_fn


@firestore_fn.on_document_created(document="users/{userId}")
def on_user_created(event: firestore_fn.Event[firestore_fn.DocumentSnapshot]) -> None:
    """Send email to admin when a new user with status=pending is created."""
    admin_email = os.environ.get("ADMIN_EMAIL")
    api_key = os.environ.get("RESEND_API_KEY")
    if not admin_email or not api_key:
        return
    snapshot = event.data
    if snapshot is None:
        return
    data = snapshot.to_dict() or {}
    if data.get("status") != "pending":
        return
    login = data.get("github_login", "unknown")
    user_email = data.get("email", "")
    _send_admin_notification(admin_email, api_key, login, user_email)


def _send_admin_notification(
    admin_email: str,
    api_key: str,
    github_login: str,
    user_email: str,
) -> None:
    """Send email to admin via Resend API."""
    payload = {
        "from": "Refactor Agent <onboarding@resend.dev>",
        "to": [admin_email],
        "subject": f"Refactor Agent: Access request from {github_login}",
        "html": (
            f"<p>A new user has requested access to Refactor Agent.</p>"
            f"<p><strong>GitHub:</strong> {github_login}</p>"
            f"<p><strong>Email:</strong> {user_email or 'not provided'}</p>"
            f"<p>Approve via Firestore console or <code>scripts/approve_user.py</code>.</p>"
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
        },
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
