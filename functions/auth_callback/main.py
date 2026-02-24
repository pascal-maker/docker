"""Cloud Function: GitHub OAuth callback for site access requests.

Exchanges authorization code for token, fetches user from GitHub, writes to
Firestore with status='pending', redirects to site.
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
USERS_COLLECTION = "users"


def _exchange_code(code: str) -> str | None:
    """Exchange GitHub OAuth code for access token."""
    client_id = os.environ.get("GITHUB_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_OAUTH_CLIENT_SECRET")
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
            payload = json.loads(resp.read().decode())
            return payload.get("access_token") or None
    except Exception:
        return None


def _fetch_github_user(token: str) -> dict | None:
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
    """Fetch primary email from /user/emails (requires user:email scope)."""
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


def _write_user_to_firestore(user_id: str, login: str, email: str | None) -> None:
    """Create or update user in Firestore with status=pending."""
    from google.cloud import firestore

    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT not set")
    db = firestore.Client(project=project)
    doc_ref = db.collection(USERS_COLLECTION).document(user_id)
    doc = doc_ref.get()
    if doc.exists:
        return
    doc_ref.set(
        {
            "github_login": login,
            "email": email,
            "created_at": firestore.SERVER_TIMESTAMP,
            "status": "pending",
        }
    )


@functions_framework.http
def auth_callback(request):
    """Handle GitHub OAuth callback: exchange code, create user, redirect."""
    code = request.args.get("code")
    base_url = os.environ.get("SITE_URL", "http://localhost:5173")
    success_url = f"{base_url.rstrip('/')}/success"
    error_url = f"{base_url.rstrip('/')}/error"

    if not code:
        return ("", 302, {"Location": error_url})

    token = _exchange_code(code)
    if not token:
        return ("", 302, {"Location": error_url})

    user_data = _fetch_github_user(token)
    if not user_data:
        return ("", 302, {"Location": error_url})

    user_id = str(user_data["id"])
    login = user_data["login"]
    email = user_data.get("email") or _fetch_primary_email(token)

    try:
        _write_user_to_firestore(user_id, login, email)
    except Exception:
        return ("", 302, {"Location": error_url})

    return ("", 302, {"Location": success_url})
