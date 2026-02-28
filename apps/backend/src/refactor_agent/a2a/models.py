"""Pydantic models for A2A executor: rename params and orchestrator state."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from refactor_agent.orchestrator.runner import RunState


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    # JSON-RPC spec allows arbitrary data here
    data: object | None = None


class MessagePart(BaseModel):
    """A single part of a message (e.g. text)."""

    kind: str
    text: str = ""


class TaskStatusMessage(BaseModel):
    """Status message with parts."""

    parts: list[MessagePart] = []


class TaskStatus(BaseModel):
    """Task status with state and optional message."""

    state: str = ""
    message: TaskStatusMessage | None = None


class TaskResult(BaseModel):
    """Result of tasks/get (task payload)."""

    kind: str = ""
    id: str = ""
    context_id: str = Field(default="", alias="contextId")
    status: TaskStatus | None = None
    artifacts: list[object] | None = None  # expand later if needed

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class MessageResult(BaseModel):
    """Result of message/send when it returns a message (no task)."""

    kind: str = "message"
    parts: list[MessagePart] = []

    model_config = ConfigDict(extra="ignore")


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response envelope."""

    result: TaskResult | MessageResult | None = None
    error: JsonRpcError | None = None

    model_config = ConfigDict(extra="ignore")


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


RenameParams = UseReplicaRenameParams


class OrchestratorStateEntry(BaseModel):
    """Stored state for pause/resume: message_history, workspace_dir, options."""

    message_history: RunState
    workspace_dir: str
    use_replica: bool = False
    language: str = "python"


class StateStore(RootModel[dict[str, OrchestratorStateEntry]]):
    """Wrapper for task_id -> OrchestratorStateEntry map (no dict in signatures)."""
