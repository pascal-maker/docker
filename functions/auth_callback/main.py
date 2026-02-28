"""Cloud Function: GitHub App OAuth callback for site access requests.

Exchanges authorization code for user-to-server token, fetches user and
installations from GitHub, writes to Firestore with status='pending' and
allowed_repos, redirects to site or vscode:// for extension.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

import functions_framework

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
GITHUB_INSTALLATIONS_URL = "https://api.github.com/user/installations"
USERS_COLLECTION = "users"
INSTALLATION_USERS_COLLECTION = "installation_users"


def _exchange_code(code: str) -> dict | None:  # noqa: no-dict-sig  # GitHub OAuth API returns JSON
    """Exchange GitHub App OAuth code for access token. Returns full response."""
    client_id = os.environ.get("GITHUB_APP_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_APP_CLIENT_SECRET")
    redirect_uri = os.environ.get("GITHUB_OAUTH_REDIRECT_URI")
    if not all([client_id, client_secret, redirect_uri]):
        return None
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code.strip(),
        "redirect_uri": redirect_uri,
    }
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        GITHUB_TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode())
    except Exception:
        return None


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
    """Fetch user installations. Returns list of {id, ...}."""
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
    """Fetch repos for an installation. Returns list of {full_name, id}."""
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


def _redirect_to(url: str, status: int = 302) -> tuple[str, int, dict[str, str]]:  # noqa: no-dict-sig  # Flask response
    """Return HTTP redirect response."""
    return ("", status, {"Location": url})


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
    """Create or update user in Firestore with status and allowed_repos."""
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


def _resolve_redirect_url(base_url: str, state: str, token: str) -> str:
    """Build redirect URL based on state (vscode vs site success)."""
    base = base_url.rstrip("/")
    if "return:vscode" in state or "vscode" in state.lower():
        token_param = urllib.parse.quote(token, safe="")
        return f"{base}/auth/success?token={token_param}"
    return f"{base}/success"


@functions_framework.http
def auth_callback(request):
    """Handle GitHub App OAuth callback: exchange code, create user, redirect."""
    code = request.args.get("code")
    state = request.args.get("state", "")
    base_url = os.environ.get("SITE_URL", "http://localhost:5173")
    error_url = f"{base_url.rstrip('/')}/error"

    if not code:
        return _redirect_to(error_url)

    token_response = _exchange_code(code)
    token = token_response.get("access_token") if token_response else None
    if not token:
        return _redirect_to(error_url)

    user_data = _fetch_github_user(token)
    if not user_data:
        return _redirect_to(error_url)

    user_id = str(user_data["id"])
    login = user_data["login"]
    email = user_data.get("email") or _fetch_primary_email(token)

    installations = _fetch_installations(token)
    allowed_repos_list, installation_ids_list = _collect_repos_and_installation_ids(
        token, installations
    )

    try:
        _write_user_to_firestore(
            user_id, login, email, allowed_repos_list, installation_ids_list
        )
    except Exception:
        return _redirect_to(error_url)

    redirect_url = _resolve_redirect_url(base_url, state, token)
    return _redirect_to(redirect_url)
