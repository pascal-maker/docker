"""Pydantic models for GitHub webhook payload."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RepoRef(BaseModel):
    """Repository reference from webhook payload."""

    full_name: str = Field(description="e.g. owner/repo")
    id: int = Field(description="GitHub repo ID")

    model_config = ConfigDict(extra="ignore")


class GitHubInstallationRef(BaseModel):
    """Installation reference from webhook payload."""

    id: int

    model_config = ConfigDict(extra="ignore")


class GitHubWebhookPayload(BaseModel):
    """GitHub App installation_repositories webhook payload."""

    action: str
    installation: GitHubInstallationRef
    repositories_added: list[RepoRef] = Field(default_factory=list)
    repositories_removed: list[RepoRef] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")
