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
from models import GitHubWebhookPayload, RepoRef
from pydantic import ValidationError

from functions_shared import HttpResponse, http_handler

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
    to_add: list[RepoRef],
    to_remove: list[RepoRef],
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
    remove_ids = {r.id for r in to_remove}
    current = [
        r
        for r in current
        if (r.get("id") if isinstance(r, dict) else None) not in remove_ids
    ]
    add_map = {r.id: r for r in to_add}
    for r in current:
        if isinstance(r, dict) and r.get("id") in add_map:
            del add_map[r["id"]]
    for r in add_map.values():
        current.append(r.model_dump())
    doc_ref.update({"allowed_repos": current})


def _validate_request(
    request,
) -> tuple[tuple[str, GitHubWebhookPayload, str] | None, tuple[str, int] | None]:
    """Validate request; return ((project, payload, action), None) or (None, error)."""
    if request.method != "POST":
        return None, ("Method not allowed", 405)
    if not (secret := os.environ.get("GITHUB_WEBHOOK_SECRET")) or not (
        project := os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT")
    ):
        return None, ("Webhook not configured", 503)
    if not _verify_signature(
        request.get_data(),
        request.headers.get("X-Hub-Signature-256"),
        secret,
    ):
        return None, ("Invalid signature", 401)
    try:
        raw = json.loads(request.get_data().decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, ("Invalid JSON", 400)
    try:
        payload = GitHubWebhookPayload.model_validate(raw)
    except ValidationError:
        return None, ("Invalid payload", 400)
    if payload.action not in ("added", "removed"):
        return None, ("OK", 200)
    return (project, payload, payload.action), None


def _process_installation_repos(
    project: str,
    installation_id: int,
    action: str,
    repos_added: list[RepoRef],
    repos_removed: list[RepoRef],
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
@http_handler
def github_webhook(request) -> HttpResponse:
    """Handle GitHub App webhook: installation_repositories."""
    validated, error = _validate_request(request)
    if error is not None:
        msg, status = error
        return HttpResponse(body=msg, status=status)

    project, payload, action = validated
    repos_added = payload.repositories_added
    repos_removed = payload.repositories_removed

    _process_installation_repos(
        project,
        payload.installation.id,
        action,
        repos_added,
        repos_removed,
    )
    return HttpResponse(body="OK", status=200)
