"""Firestore-backed UserStore: get/create user, ban check, rate limit, audit log."""

from __future__ import annotations

import asyncio
import os
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from google.cloud.firestore import transactional

from refactor_agent.auth.logger import logger
from refactor_agent.auth.models import AuditLogEntry, GitHubUser, RepoAccess, UserRecord

if TYPE_CHECKING:
    from google.cloud.firestore_v1 import Client, DocumentSnapshot, Transaction

USERS_COLLECTION = "users"
INSTALLATION_USERS_COLLECTION = "installation_users"
AUDIT_LOGS_COLLECTION = "audit_logs"
USAGE_WINDOWS_COLLECTION = "usage_windows"
BAN_CACHE_TTL_SECS = 30.0
DEFAULT_RATE_LIMIT = 60
DEFAULT_RATE_WINDOW_SECS = 60


def _get_firestore_client() -> Client | None:
    """Return Firestore client if project is configured, else None."""
    try:
        from google.cloud.firestore import Client as FirestoreClient
    except ImportError:
        return None
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if not project:
        return None
    return FirestoreClient(project=project)


class UserStore:
    """Firestore-backed store for users, rate limits, and audit logs."""

    def __init__(self, client: Client | None = None) -> None:
        """Initialize with optional Firestore client (default: from env)."""
        self._client = client if client is not None else _get_firestore_client()
        self._ban_cache: dict[str, tuple[bool, float]] = {}

    def _db(self) -> Client:
        """Return Firestore client; raise if not configured."""
        if self._client is None:
            raise RuntimeError(
                "Firestore not configured: set GOOGLE_CLOUD_PROJECT or pass client"
            )
        return self._client

    def is_available(self) -> bool:
        """Return True if Firestore is configured and usable."""
        return self._client is not None

    async def get_or_create_user(
        self,
        github_user: GitHubUser,
        *,
        onboarding_mode: str = "alpha",
        allowed_repos: list[RepoAccess] | None = None,
    ) -> UserRecord:
        """Get existing user or create with status based on onboarding_mode.

        Alpha: new users get status='pending'. Beta: new users get status='active'.
        """
        db = self._db()
        user_id = str(github_user.id)
        doc_ref = db.collection(USERS_COLLECTION).document(user_id)

        def _parse_allowed_repos(data: list[object]) -> list[RepoAccess]:
            return [
                RepoAccess(full_name=item["full_name"], id=item["id"])
                for item in data or []
                if isinstance(item, dict) and "full_name" in item and "id" in item
            ]

        def _get_or_create() -> UserRecord:
            doc = cast("DocumentSnapshot", doc_ref.get())
            if doc.exists:
                data = doc.to_dict() or {}
                created_raw = data.get("created_at")
                if (
                    created_raw is not None
                    and hasattr(created_raw, "timestamp")
                    and callable(getattr(created_raw, "timestamp", None))
                ):
                    created_at = datetime.fromtimestamp(created_raw.timestamp(), tz=UTC)
                else:
                    created_at = datetime.now(UTC)
                return UserRecord(
                    id=user_id,
                    github_login=data.get("github_login", github_user.login),
                    email=data.get("email") or github_user.email,
                    created_at=created_at,
                    status=data.get("status", "active"),
                    ban_reason=data.get("ban_reason"),
                    rate_limit_override=data.get("rate_limit_override"),
                    allowed_repos=_parse_allowed_repos(data.get("allowed_repos", [])),
                )
            initial_status = "active" if onboarding_mode == "beta" else "pending"
            repos = allowed_repos or []
            record = UserRecord(
                id=user_id,
                github_login=github_user.login,
                email=github_user.email,
                status=initial_status,
                allowed_repos=repos,
            )
            payload: dict[str, object] = {
                "github_login": record.github_login,
                "email": record.email,
                "created_at": record.created_at,
                "status": record.status,
                "allowed_repos": [
                    {"full_name": r.full_name, "id": r.id} for r in repos
                ],
            }
            doc_ref.set(payload)
            return record

        return await asyncio.to_thread(_get_or_create)

    async def update_user_repos(
        self, user_id: str, allowed_repos: list[RepoAccess]
    ) -> None:
        """Update allowed_repos for a user (e.g. from webhook)."""
        db = self._db()
        doc_ref = db.collection(USERS_COLLECTION).document(user_id)

        def _update() -> None:
            doc_ref.update(
                {
                    "allowed_repos": [
                        {"full_name": r.full_name, "id": r.id} for r in allowed_repos
                    ],
                }
            )

        await asyncio.to_thread(_update)

    async def update_installation_users(
        self, installation_id: int, user_ids: list[str]
    ) -> None:
        """Store mapping of installation_id -> user_ids for webhook lookups."""
        db = self._db()
        doc_ref = db.collection(INSTALLATION_USERS_COLLECTION).document(
            str(installation_id)
        )

        def _set() -> None:
            doc_ref.set({"user_ids": user_ids})

        await asyncio.to_thread(_set)

    async def get_installation_user_ids(self, installation_id: int) -> list[str]:
        """Get user_ids for an installation (for webhook)."""
        db = self._db()
        doc = cast(
            "DocumentSnapshot",
            db.collection(INSTALLATION_USERS_COLLECTION)
            .document(str(installation_id))
            .get(),
        )
        if not doc.exists:
            return []
        data = doc.to_dict() or {}
        ids = data.get("user_ids", [])
        return [str(x) for x in ids] if isinstance(ids, list) else []

    def is_banned(self, user_id: str) -> bool:
        """Check if user is banned; uses short TTL in-process cache."""
        now = time.monotonic()
        if user_id in self._ban_cache:
            cached, expires = self._ban_cache[user_id]
            if now < expires:
                return cached
        try:
            db = self._db()
            doc = cast(
                "DocumentSnapshot",
                db.collection(USERS_COLLECTION).document(user_id).get(),
            )
            banned = (doc.to_dict() or {}).get("status") == "banned"
            self._ban_cache[user_id] = (banned, now + BAN_CACHE_TTL_SECS)
            return banned
        except Exception as e:
            logger.warning("is_banned check failed", user_id=user_id, error=str(e))
            return False

    async def check_and_increment_rate_limit(
        self,
        user_id: str,
        limit: int = DEFAULT_RATE_LIMIT,
        window_secs: int = DEFAULT_RATE_WINDOW_SECS,
    ) -> bool:
        """Check rate limit and increment. True if allowed, False if exceeded."""
        db = self._db()
        window_start = int(time.time() / window_secs) * window_secs
        doc_id = f"{user_id}_{window_start}"
        doc_ref = db.collection(USAGE_WINDOWS_COLLECTION).document(doc_id)

        def _check_and_inc() -> bool:
            txn = db.transaction()

            @transactional
            def _in_transaction(trans: Transaction) -> bool:
                snapshot = cast(
                    "DocumentSnapshot",
                    doc_ref.get(transaction=trans),
                )
                data = snapshot.to_dict() or {}
                count = data.get("count", 0)
                if count >= limit:
                    return False
                payload = {
                    "count": count + 1,
                    "window_start": window_start,
                    "window_end": window_start + window_secs,
                }
                trans.set(doc_ref, payload, merge=True)
                return True

            return _in_transaction(txn)

        try:
            return await asyncio.to_thread(_check_and_inc)
        except Exception as e:
            logger.warning("rate limit check failed", user_id=user_id, error=str(e))
            return True

    async def write_audit_log(self, entry: AuditLogEntry) -> None:
        """Write audit log entry (fire-and-forget, non-blocking)."""
        db = self._db()
        coll = db.collection(AUDIT_LOGS_COLLECTION)

        def _write() -> None:
            coll.add(
                {
                    "user_id": entry.user_id,
                    "github_login": entry.github_login,
                    "timestamp": entry.timestamp,
                    "path": entry.path,
                    "method": entry.method,
                    "status_code": entry.status_code,
                    "duration_ms": entry.duration_ms,
                }
            )

        _task = asyncio.create_task(asyncio.to_thread(_write))
