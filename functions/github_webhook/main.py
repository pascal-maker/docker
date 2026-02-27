"""Cloud Function: GitHub App webhook handler for installation_repositories.

Updates allowed_repos in Firestore when users add or remove repos from the
GitHub App installation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os

import functions_framework

USERS_COLLECTION = "users"
INSTALLATION_USERS_COLLECTION = "installation_users"


def _verify_signature(payload_body: bytes, signature: str | None, secret: str) -> bool:
    """Verify GitHub webhook signature (X-Hub-Signature-256)."""
    if not signature or not signature.startswith("sha256="):
        return False
    sig_hex = signature[7:]
    secret_bytes = secret.encode() if isinstance(secret, str) else secret
    expected = hmac.new(secret_bytes, payload_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig_hex, expected)


def _update_user_repos(
    project: str,
    user_id: str,
    to_add: list[dict],
    to_remove: list[dict],
) -> None:
    """Add and remove repos from user's allowed_repos."""
    from google.cloud import firestore

    db = firestore.Client(project=project)
    doc_ref = db.collection(USERS_COLLECTION).document(user_id)
    doc = doc_ref.get()
    if not doc.exists:
        return
    data = doc.to_dict() or {}
    current = list(data.get("allowed_repos", []))
    remove_ids = {r["id"] for r in to_remove if isinstance(r, dict) and "id" in r}
    current = [r for r in current if r.get("id") not in remove_ids]
    add_map = {
        r["id"]: r
        for r in to_add
        if isinstance(r, dict) and "id" in r and "full_name" in r
    }
    for r in current:
        if isinstance(r, dict) and r.get("id") in add_map:
            del add_map[r["id"]]
    for r in add_map.values():
        current.append({"full_name": r["full_name"], "id": r["id"]})
    doc_ref.update({"allowed_repos": current})


def _validate_request(
    request,
) -> tuple[tuple[str, dict, str] | None, tuple[str, int] | None]:
    """Validate request; return ((project, payload, action), None) or (None, error)."""
    result: tuple[tuple[str, dict, str] | None, tuple[str, int] | None] = (None, None)

    if request.method != "POST":
        result = None, ("Method not allowed", 405)
    elif not (secret := os.environ.get("GITHUB_WEBHOOK_SECRET")) or not (
        project := os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
    ):
        result = None, ("Webhook not configured", 503)
    elif not _verify_signature(
        request.get_data(),
        request.headers.get("X-Hub-Signature-256"),
        secret,
    ):
        result = None, ("Invalid signature", 401)
    else:
        try:
            payload = json.loads(request.get_data().decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            result = None, ("Invalid JSON", 400)
        else:
            action = payload.get("action")
            installation = payload.get("installation") or {}
            if action not in ("added", "removed"):
                result = None, ("OK", 200)
            elif installation.get("id") is None:
                result = None, ("Missing installation", 400)
            else:
                result = (project, payload, action), None

    return result


def _process_installation_repos(
    project: str,
    installation_id: int,
    action: str,
    repos_added: list,
    repos_removed: list,
) -> None:
    """Update allowed_repos for all users in this installation."""
    from google.cloud import firestore

    db = firestore.Client(project=project)
    inst_ref = db.collection(INSTALLATION_USERS_COLLECTION).document(
        str(installation_id)
    )
    inst_doc = inst_ref.get()
    if not inst_doc.exists:
        return

    data = inst_doc.to_dict() or {}
    user_ids = data.get("user_ids", [])
    if not isinstance(user_ids, list):
        user_ids = []

    to_add = repos_added if action == "added" else []
    to_remove = repos_removed if action == "removed" else []
    for user_id in user_ids:
        _update_user_repos(project, str(user_id), to_add, to_remove)


@functions_framework.http
def github_webhook(request):
    """Handle GitHub App webhook: installation_repositories."""
    validated, error = _validate_request(request)
    if error is not None:
        return error

    project, payload, action = validated
    repos_added = payload.get("repositories_added", [])
    repos_removed = payload.get("repositories_removed", [])

    _process_installation_repos(
        project,
        payload["installation"]["id"],
        action,
        repos_added,
        repos_removed,
    )
    return ("OK", 200)
