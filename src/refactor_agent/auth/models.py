"""Pydantic models for auth: user records, audit log, GitHub user."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """GitHub user identity from API."""

    id: int
    login: str
    email: str | None = None


class RepoAccess(BaseModel):
    """Repository access from GitHub App installation."""

    full_name: str = Field(description="e.g. owner/repo")
    id: int = Field(description="GitHub repo ID")


class UserRecord(BaseModel):
    """Firestore user document."""

    id: str = Field(description="GitHub user ID as string")
    github_login: str
    email: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = Field(description="pending | active | banned | suspended")
    ban_reason: str | None = None
    rate_limit_override: int | None = None
    allowed_repos: list[RepoAccess] = Field(default_factory=list)


class AuditLogEntry(BaseModel):
    """Single audit log entry for Firestore."""

    user_id: str
    github_login: str
    timestamp: datetime = Field(default_factory=datetime.now)
    path: str
    method: str
    status_code: int
    duration_ms: float
