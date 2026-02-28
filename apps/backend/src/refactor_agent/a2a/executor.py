"""A2A executor: shared orchestrator; translate message, run, emit artifacts."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    DataPart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from pydantic import ValidationError
from pydantic_ai import Agent

from refactor_agent.a2a.models import (
    OrchestratorStateEntry,
    PromptOnlyPayload,
    StateStore,
    UseReplicaRenameParams,
)
from refactor_agent.orchestrator import (
    NeedInputResult,
    OrchestratorDeps,
    create_orchestrator_agent,
    run_orchestrator,
)

REPLICA_DIR_ENV = "REPLICA_DIR"
ORCHESTRATOR_STATE_KEY = "orchestrator_state"

_FILE_EXT_BY_LANG = {"python": "*.py", "typescript": "*.ts"}


def _language_and_ext(parsed: UseReplicaRenameParams) -> tuple[str, str]:
    """Return (language, file_ext) from parsed params."""
    return parsed.language, _FILE_EXT_BY_LANG[parsed.language]


# task_id -> state for pause/resume
_orchestrator_state: dict[str, OrchestratorStateEntry] = {}

_ARTIFACT_PREVIEW_LEN = 200


def _agent_message(text: str) -> Message:
    return Message(
        message_id=uuid.uuid4().hex,
        role=Role.agent,
        parts=[Part(root=TextPart(text=text))],
    )


def _status_event(
    task_id: str,
    context_id: str,
    state: TaskState,
    message_text: str,
    *,
    final: bool = True,
) -> TaskStatusUpdateEvent:
    return TaskStatusUpdateEvent(
        task_id=task_id,
        context_id=context_id,
        status=TaskStatus(state=state, message=_agent_message(message_text)),
        final=final,
    )


def _parse_prompt_only(data: PromptOnlyPayload) -> tuple[str, str] | str:
    """Parse prompt-only payload. Returns (prompt, lang) or error string."""
    if data.use_replica is not True:
        return "ERROR: use_replica must be true. Push workspace via sync service first."
    prompt_val = data.prompt or data.user_message or data.text
    if not prompt_val or not str(prompt_val).strip():
        return "ERROR: missing or empty 'prompt' (required for free-form requests)"
    lang_val = data.language
    lang: str = "python" if lang_val not in ("python", "typescript") else str(lang_val)
    return (str(prompt_val).strip(), lang)


ParseResult = UseReplicaRenameParams | tuple[str, str, str] | str


def _parse_rename_params(user_input: str) -> ParseResult:
    """Parse JSON into validated rename params. Returns model or error string."""
    try:
        data = json.loads(user_input)
    except json.JSONDecodeError as e:
        return f"ERROR: invalid JSON: {e}"
    if not isinstance(data, dict):
        return "ERROR: root must be a JSON object"

    if data.get("use_replica") is not True:
        return "ERROR: use_replica must be true. Push workspace via sync service first."

    old_name = data.get("old_name")
    new_name = data.get("new_name")
    # Prompt-only: no old_name/new_name required
    if not isinstance(old_name, str) or not isinstance(new_name, str):
        payload_data = PromptOnlyPayload.model_validate(data)
        prompt_result = _parse_prompt_only(payload_data)
        if isinstance(prompt_result, str):
            return prompt_result
        # Return a special marker that executor handles as prompt-only
        return ("__PROMPT_ONLY__", prompt_result[0], prompt_result[1])

    scope_node = data.get("scope_node")
    if scope_node is not None and not isinstance(scope_node, str):
        return "ERROR: 'scope_node' must be a string or null"

    lang = data.get("language")
    if lang not in ("python", "typescript"):
        lang = "python"
    payload: dict[str, str | None | bool] = {
        "old_name": old_name,
        "new_name": new_name,
        "scope_node": scope_node,
        "use_replica": True,
        "language": lang,
    }
    prompt_val = data.get("prompt") or data.get("user_message")
    if isinstance(prompt_val, str):
        payload["prompt"] = prompt_val
    try:
        return UseReplicaRenameParams.model_validate(payload)
    except ValidationError as e:
        return f"ERROR: {e}"


def _internal_message_from_parsed(parsed: UseReplicaRenameParams, lang: str) -> str:
    """Build the prompt we send to the orchestrator when no raw prompt is provided."""
    kind = "TypeScript" if lang == "typescript" else "Python"
    return (
        f"Rename the {kind} symbol '{parsed.old_name}' to '{parsed.new_name}' across the "
        "workspace. Use the rename_in_workspace tool to apply the rename."
    )


def _artifact_from_modified_file(
    task_id: str,
    context_id: str,
    path: str,
    modified_source: str,
    *,
    append: bool = False,
) -> TaskArtifactUpdateEvent:
    """Build a rename-result artifact from path and modified source."""
    data: dict[str, str | None] = {
        "summary": f"Modified {path}",
        "modified_source": modified_source,
        "path": path,
    }
    artifact = Artifact(
        artifact_id=uuid.uuid4().hex,
        name="rename-result",
        description="Refactored source; apply modified_source to path.",
        parts=[
            Part(
                root=TextPart(
                    text=modified_source[:_ARTIFACT_PREVIEW_LEN]
                    + ("..." if len(modified_source) > _ARTIFACT_PREVIEW_LEN else "")
                )
            ),
            Part(root=DataPart(data=data)),
        ],
    )
    return TaskArtifactUpdateEvent(
        task_id=task_id,
        context_id=context_id,
        artifact=artifact,
        append=append,
    )


async def _emit_artifacts_from_workspace(
    workspace_dir: Path,
    task_id: str,
    context_id: str,
    event_queue: EventQueue,
    *,
    lang: str = "python",
) -> None:
    """Emit one rename-result artifact per workspace file (by language)."""
    patterns = ("*.ts", "*.tsx") if lang == "typescript" else ("*.py",)
    for pattern in patterns:
        for fp in sorted(workspace_dir.rglob(pattern)):  # noqa: ASYNC240 — sync rglob in artifact emit
            if not fp.is_file():
                continue
            rel = fp.relative_to(workspace_dir)
            path_str = str(rel).replace("\\", "/")
            content = fp.read_text(encoding="utf-8")
            await event_queue.enqueue_event(
                _artifact_from_modified_file(
                    task_id,
                    context_id,
                    path_str,
                    content,
                    append=False,
                )
            )


class ASTRefactorAgentExecutor(AgentExecutor):
    """Translate A2A message, run orchestrator, emit input_required or artifacts."""

    def __init__(
        self,
        state_store: StateStore | None = None,
        agent: Agent[OrchestratorDeps, str] | None = None,
    ) -> None:
        self._state_store: dict[str, OrchestratorStateEntry] = (
            state_store.root if state_store is not None else _orchestrator_state
        )
        self._agent: Agent[OrchestratorDeps, str] = (
            agent if agent is not None else create_orchestrator_agent()
        )

    @override
    async def execute(  # noqa: C901, PLR0912 — message dispatch and artifact handling
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Run orchestrator; emit input_required or artifacts."""
        user_input = (context.get_user_input() or "").strip()
        task_id = context.task_id
        context_id = context.context_id
        if task_id is None or context_id is None:
            await event_queue.enqueue_event(
                _agent_message("ERROR: missing task_id or context_id")
            )
            return
        # A2A RequestContext has no typed stub; access optional current_task.
        current_task = getattr(context, "current_task", None)

        # Resumption: we were waiting for user input
        saved = self._state_store.get(task_id)
        if (
            saved is not None
            and current_task is not None
            and current_task.status.state == TaskState.input_required
        ):
            message_history = saved.message_history
            workspace_dir_str = saved.workspace_dir
            workspace_dir = Path(workspace_dir_str)
            if not workspace_dir.exists():  # noqa: ASYNC240 — sync Path check before cleanup
                del self._state_store[task_id]
                await event_queue.enqueue_event(
                    _status_event(
                        task_id,
                        context_id,
                        TaskState.failed,
                        "Session expired; please submit the request again.",
                    )
                )
                return
            lang = saved.language
            ext = _FILE_EXT_BY_LANG.get(lang, "*.py")
            deps = OrchestratorDeps(
                language=lang,
                workspace=workspace_dir,
                mode="Ask",
                file_ext=ext,
                get_user_input=None,
            )
            result, run_state = await run_orchestrator(
                self._agent,
                deps,
                user_input,
                message_history=message_history,
            )
            if isinstance(result, NeedInputResult):
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        task_id=task_id,
                        context_id=context_id,
                        artifact=Artifact(
                            artifact_id=uuid.uuid4().hex,
                            name="refactor-input-required",
                            description=result.need_input.message,
                            parts=[
                                Part(root=TextPart(text=result.need_input.message)),
                                Part(
                                    root=DataPart(
                                        data=result.need_input.payload.model_dump()
                                    )
                                ),
                            ],
                        ),
                        append=False,
                    )
                )
                await event_queue.enqueue_event(
                    _status_event(
                        task_id,
                        context_id,
                        TaskState.input_required,
                        result.need_input.message,
                        final=False,
                    )
                )
                self._state_store[task_id] = OrchestratorStateEntry(
                    message_history=run_state,
                    workspace_dir=workspace_dir_str,
                    use_replica=saved.use_replica,
                    language=lang,
                )
                return
            await _emit_artifacts_from_workspace(
                workspace_dir,
                task_id,
                context_id,
                event_queue,
                lang=lang,
            )
            await event_queue.enqueue_event(
                _status_event(
                    task_id,
                    context_id,
                    TaskState.completed,
                    result.output,
                )
            )
            use_replica_saved = saved.use_replica
            del self._state_store[task_id]
            if not use_replica_saved and workspace_dir.exists():  # noqa: ASYNC240 — sync Path check before rmtree
                shutil.rmtree(workspace_dir, ignore_errors=True)
            return

        # Initial request
        if not user_input:
            await event_queue.enqueue_event(
                _status_event(
                    task_id,
                    context_id,
                    TaskState.failed,
                    "ERROR: empty input. Send JSON with refactor request (e.g. "
                    "old_name, new_name, use_replica: true). Push workspace via sync first.",
                )
            )
            return

        parsed = _parse_rename_params(user_input)
        if isinstance(parsed, str):
            await event_queue.enqueue_event(
                _status_event(task_id, context_id, TaskState.failed, parsed)
            )
            return

        replica_dir = os.environ.get(REPLICA_DIR_ENV, "/workspace")
        workspace_dir = Path(replica_dir)
        if not workspace_dir.exists():
            await event_queue.enqueue_event(
                _status_event(
                    task_id,
                    context_id,
                    TaskState.failed,
                    "use_replica is true but REPLICA_DIR does not exist; "
                    "push workspace via sync service first.",
                )
            )
            return

        use_replica = True
        # Prompt-only (free-form user message)
        if isinstance(parsed, tuple):
            _prompt, lang = parsed[1], parsed[2]
            file_ext = _FILE_EXT_BY_LANG.get(lang, "*.py")
            deps = OrchestratorDeps(
                language=lang,
                workspace=workspace_dir,
                mode="Ask",
                file_ext=file_ext,
                get_user_input=None,
            )
            internal_message = _prompt
        else:
            lang, file_ext = _language_and_ext(parsed)
            deps = OrchestratorDeps(
                language=lang,
                workspace=workspace_dir,
                mode="Ask",
                file_ext=file_ext,
                get_user_input=None,
            )
            raw_prompt = parsed.prompt
            if raw_prompt is not None and raw_prompt.strip():
                internal_message = raw_prompt.strip()
            else:
                internal_message = _internal_message_from_parsed(parsed, lang)
        result, run_state = await run_orchestrator(
            self._agent,
            deps,
            internal_message,
            message_history=None,
        )
        if isinstance(result, NeedInputResult):
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    task_id=task_id,
                    context_id=context_id,
                    artifact=Artifact(
                        artifact_id=uuid.uuid4().hex,
                        name="refactor-input-required",
                        description=result.need_input.message,
                        parts=[
                            Part(root=TextPart(text=result.need_input.message)),
                            Part(
                                root=DataPart(
                                    data=result.need_input.payload.model_dump()
                                )
                            ),
                        ],
                    ),
                    append=False,
                )
            )
            await event_queue.enqueue_event(
                _status_event(
                    task_id,
                    context_id,
                    TaskState.input_required,
                    result.need_input.message,
                    final=False,
                )
            )
            self._state_store[task_id] = OrchestratorStateEntry(
                message_history=run_state,
                workspace_dir=str(workspace_dir),
                use_replica=use_replica,
                language=lang,
            )
            return
        await _emit_artifacts_from_workspace(
            workspace_dir,
            task_id,
            context_id,
            event_queue,
            lang=lang,
        )
        await event_queue.enqueue_event(
            _status_event(
                task_id,
                context_id,
                TaskState.completed,
                result.output,
            )
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel is not supported."""
        raise NotImplementedError("cancel not supported")
