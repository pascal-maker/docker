"""Pydantic models for A2A executor: rename params and orchestrator state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, RootModel

from refactor_agent.orchestrator.runner import RunState


class WorkspaceFile(BaseModel):
    """Single file in a workspace: path and content. Used by UI for sync payload."""

    path: str = Field(..., min_length=1)
    source: str = ""


class UseReplicaRenameParams(BaseModel):
    """Rename params when using replica dir (use_replica=true)."""

    old_name: str
    new_name: str
    scope_node: str | None = None
    use_replica: Literal[True] = True
    language: Literal["python", "typescript"] = "python"
    prompt: str | None = None


RenameParams = UseReplicaRenameParams


class OrchestratorStateEntry(BaseModel):
    """Stored state for pause/resume: message_history, workspace_dir, options."""

    message_history: RunState
    workspace_dir: str
    use_replica: bool = False
    language: str = "python"


class StateStore(RootModel[dict[str, OrchestratorStateEntry]]):
    """Wrapper for task_id -> OrchestratorStateEntry map (no dict in signatures)."""
