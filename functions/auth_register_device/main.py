"""Cloud Function: Register user from device flow token.

Accepts POST with Authorization: Bearer <token>. Verifies token is from our
GitHub App (app_id check), fetches user and installations, writes to Firestore.
Used by VS Code extension when device flow is used instead of browser redirect.
"""

from __future__ import annotations

import json
import os
import urllib.request

import functions_framework

GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
GITHUB_INSTALLATIONS_URL = "https://api.github.com/user/installations"
USERS_COLLECTION = "users"
INSTALLATION_USERS_COLLECTION = "installation_users"


def _fetch_github_user(token: str) -> dict | None:  # noqa: no-dict-sig  # GitHub API returns JSON
    """Fetch GitHub user via API."""
    req = urllib.request.Request(
        GITHUB_USER_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _fetch_primary_email(token: str) -> str | None:
    """Fetch primary email from /user/emails."""
    req = urllib.request.Request(
        GITHUB_EMAILS_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            emails = json.loads(resp.read().decode())
            for e in emails:
                if isinstance(e, dict) and e.get("primary") and e.get("verified"):
                    return e.get("email") or None
            for e in emails:
                if isinstance(e, dict) and e.get("verified"):
                    return e.get("email") or None
            return None
    except Exception:
        return None


def _fetch_installations(token: str) -> list[dict]:  # noqa: no-dict-sig  # GitHub API returns JSON
    """Fetch user installations."""
    req = urllib.request.Request(
        f"{GITHUB_INSTALLATIONS_URL}?per_page=100",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return []
            data = json.loads(resp.read().decode())
            return data.get("installations", [])
    except Exception:
        return []


def _fetch_installation_repos(token: str, installation_id: int) -> list[dict]:  # noqa: no-dict-sig  # GitHub API
    """Fetch repos for an installation."""
    url = f"https://api.github.com/user/installations/{installation_id}/repositories"
    req = urllib.request.Request(
        f"{url}?per_page=100",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return []
            data = json.loads(resp.read().decode())
            repos = data.get("repositories", [])
            return [
                {"full_name": r["full_name"], "id": r["id"]}
                for r in repos
                if isinstance(r, dict) and "full_name" in r and "id" in r
            ]
    except Exception:
        return []


def _collect_repos_and_installation_ids(  # noqa: no-dict-sig  # GitHub API list[dict]
    token: str, installations: list[dict]
) -> tuple[list[dict], list[int]]:
    """Collect allowed_repos and installation_ids from installations."""
    allowed_repos_list: list[dict] = []
    seen_repos: set[tuple[str, int]] = set()
    installation_ids_list: list[int] = []

    for inst in installations:
        inst_id = inst.get("id") if isinstance(inst, dict) else None
        if inst_id is None:
            continue
        installation_ids_list.append(inst_id)
        repos = _fetch_installation_repos(token, inst_id)
        for r in repos:
            key = (r["full_name"], r["id"])
            if key not in seen_repos:
                seen_repos.add(key)
                allowed_repos_list.append(r)

    return allowed_repos_list, installation_ids_list


def _write_user_to_firestore(  # noqa: no-dict-sig  # Firestore expects list of dicts
    user_id: str,
    login: str,
    email: str | None,
    allowed_repos: list[dict],
    installation_ids: list[int],
) -> None:
    """Create or update user in Firestore."""
    from google.cloud import firestore

    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT not set")
    db = firestore.Client(project=project)
    doc_ref = db.collection(USERS_COLLECTION).document(user_id)
    doc = doc_ref.get()

    payload: dict = {
        "github_login": login,
        "email": email,
        "allowed_repos": allowed_repos,
    }
    if not doc.exists:
        payload["created_at"] = firestore.SERVER_TIMESTAMP
        payload["status"] = "pending"
        doc_ref.set(payload)
    else:
        doc_ref.update(payload)

    for inst_id in installation_ids:
        inst_ref = db.collection(INSTALLATION_USERS_COLLECTION).document(str(inst_id))
        inst_doc = inst_ref.get()
        existing = []
        if inst_doc.exists:
            data = inst_doc.to_dict() or {}
            existing = list(data.get("user_ids", []))
        if user_id not in existing:
            existing.append(user_id)
        inst_ref.set({"user_ids": existing})


def _json_response(body: str, status: int) -> tuple[str, int, dict[str, str]]:  # noqa: no-dict-sig  # Flask response
    """Return JSON response with Content-Type header."""
    return (body, status, {"Content-Type": "application/json"})


def _validate_register_request(request) -> tuple[str | None, tuple[str, int] | None]:
    """Validate request; return (token, None) or (None, (error_json, status))."""
    if request.method != "POST":
        return None, (json.dumps({"error": "Method not allowed"}), 405)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, (
            json.dumps({"error": "Missing or invalid Authorization header"}),
            401,
        )

    token = auth[7:].strip()
    if not token:
        return None, (json.dumps({"error": "Empty token"}), 401)

    return token, None


def _filter_our_installations(  # noqa: no-dict-sig  # GitHub API list[dict]
    installations: list[dict], app_id_str: str
) -> tuple[list[dict] | None, tuple[str, int] | None]:
    """Filter to our app's installations. Return (our_installations, None) or (None, error)."""
    if not app_id_str:
        return None, (json.dumps({"error": "Server misconfiguration"}), 503)
    try:
        expected_app_id = int(app_id_str)
    except ValueError:
        return None, (json.dumps({"error": "Server misconfiguration"}), 503)
    our_installations = [
        i
        for i in installations
        if isinstance(i, dict) and i.get("app_id") == expected_app_id
    ]
    if not our_installations:
        return None, (
            json.dumps({"error": "Token not from Refactor Agent app"}),
            403,
        )
    return our_installations, None


@functions_framework.http
def auth_register_device(request):
    """Register user from device flow token. POST with Authorization: Bearer <token>."""
    token, err = _validate_register_request(request)
    if err is not None:
        return _json_response(err[0], err[1])

    user_data = _fetch_github_user(token)
    if not user_data:
        return _json_response(json.dumps({"error": "Invalid token"}), 401)

    installations = _fetch_installations(token)
    our_installations, err = _filter_our_installations(
        installations, os.environ.get("GITHUB_APP_ID", "").strip()
    )
    if our_installations is None and err is not None:
        return _json_response(err[0], err[1])

    user_id = str(user_data["id"])
    login = user_data["login"]
    email = user_data.get("email") or _fetch_primary_email(token)
    allowed_repos_list, installation_ids_list = _collect_repos_and_installation_ids(
        token, our_installations
    )

    try:
        _write_user_to_firestore(
            user_id, login, email, allowed_repos_list, installation_ids_list
        )
    except Exception:
        return _json_response(json.dumps({"error": "Failed to register user"}), 500)

    return _json_response(json.dumps({"ok": True}), 200)
