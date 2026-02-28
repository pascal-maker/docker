"""GitHub API response models for auth functions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GitHubTokenResponse(BaseModel):
    """GitHub OAuth token exchange response."""

    access_token: str
    token_type: str = "bearer"
    scope: str | None = None
    expires_in: int | None = None

    model_config = ConfigDict(extra="ignore")


class GitHubUser(BaseModel):
    """GitHub user from /user API."""

    id: int
    login: str
    email: str | None = None

    model_config = ConfigDict(extra="ignore")


class RepoAccess(BaseModel):
    """Repository access from GitHub App installation."""

    full_name: str = Field(description="e.g. owner/repo")
    id: int = Field(description="GitHub repo ID")

    model_config = ConfigDict(extra="ignore")


class GitHubInstallation(BaseModel):
    """GitHub App installation (minimal for filtering)."""

    id: int
    app_id: int | None = None

    model_config = ConfigDict(extra="ignore")
