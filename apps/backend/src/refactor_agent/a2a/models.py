"""Pydantic models for A2A executor: rename params and orchestrator state."""

from __future__ import annotations

from typing import Any, Literal

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


class PromptOnlyPayload(BaseModel):
    """Prompt-only payload: use_replica, prompt/user_message/text, language."""

    use_replica: bool = False
    prompt: str | None = None
    user_message: str | None = None
    text: str | None = None
    language: str | None = None


class HttpHeaders(RootModel[dict[str, str]]):
    """HTTP headers dict for request/response. Use .root for dict access."""


class MessageSendPayload(BaseModel):
    """Payload for A2A message/send (rename task)."""

    source: str = ""
    old_name: str = ""
    new_name: str = ""


class JsonRpcResponse(RootModel[dict[str, Any]]):
    """JSON-RPC 2.0 response. Use .root for dict access."""


RenameParams = UseReplicaRenameParams


class OrchestratorStateEntry(BaseModel):
    """Stored state for pause/resume: message_history, workspace_dir, options."""

    message_history: RunState
    workspace_dir: str
    use_replica: bool = False
    language: str = "python"


class StateStore(RootModel[dict[str, OrchestratorStateEntry]]):
    """Wrapper for task_id -> OrchestratorStateEntry map (no dict in signatures)."""
