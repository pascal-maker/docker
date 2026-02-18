"""A2A AgentExecutor: single refactor task type (rename_symbol) using LibCSTEngine."""

from __future__ import annotations

import json
import uuid

# RequestContext and EventQueue used in method signatures at runtime
from a2a.server.agent_execution import AgentExecutor, RequestContext  # noqa: TC002
from a2a.server.events import EventQueue  # noqa: TC002
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

# CollisionInfo used at runtime for collision list type
from document_structuring_agent.ast_refactor.engine import (  # noqa: TC001
    CollisionInfo,
    LibCSTEngine,
)

PENDING_RENAME_KEY = "pending_rename"
RENAME_RESULT_KEY = "rename_result"
MODIFIED_SOURCE_MARKER = "\n\n--- Modified source ---\n"


def _agent_message(text: str) -> Message:
    """Build an A2A Message with role=agent and a single text part."""
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
    """Build TaskStatusUpdateEvent so the bridge receives result.id, result.status."""
    return TaskStatusUpdateEvent(
        task_id=task_id,
        context_id=context_id,
        status=TaskStatus(state=state, message=_agent_message(message_text)),
        final=final,
    )


def _parse_rename_params(user_input: str) -> dict[str, str | None] | str:  # noqa: PLR0911, PLR0912, C901 — single- and multi-file validation
    """Parse JSON to rename params. Returns dict or error string."""
    try:
        data = json.loads(user_input)
    except json.JSONDecodeError as e:
        return f"ERROR: invalid JSON: {e}"
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    scope_node = data.get("scope_node")
    if not isinstance(old_name, str):
        return "ERROR: missing or invalid 'old_name' (must be a string)"
    if not isinstance(new_name, str):
        return "ERROR: missing or invalid 'new_name' (must be a string)"
    if scope_node is not None and not isinstance(scope_node, str):
        return "ERROR: 'scope_node' must be a string or null"

    workspace = data.get("workspace")
    if isinstance(workspace, list) and len(workspace) > 0:
        # Workspace: agent finds impact by trying rename in each file
        out_workspace: list[dict[str, str]] = []
        for i, item in enumerate(workspace):
            if not isinstance(item, dict):
                return f"ERROR: 'workspace[{i}]' must be an object"
            p = item.get("path")
            s = item.get("source")
            if not isinstance(p, str) or not p.strip():
                return f"ERROR: 'workspace[{i}].path' must be a non-empty string"
            if not isinstance(s, str):
                return f"ERROR: 'workspace[{i}].source' must be a string"
            out_workspace.append({"path": p, "source": s})
        return {
            "workspace": out_workspace,
            "old_name": old_name,
            "new_name": new_name,
            "scope_node": scope_node,
            "source": None,
            "path": None,
            "files": None,
        }

    files = data.get("files")
    if isinstance(files, list) and len(files) > 0:
        # Multi-file: each item must have path and source
        out_files: list[dict[str, str]] = []
        for i, item in enumerate(files):
            if not isinstance(item, dict):
                return f"ERROR: 'files[{i}]' must be an object"
            p = item.get("path")
            s = item.get("source")
            if not isinstance(p, str) or not p.strip():
                return f"ERROR: 'files[{i}].path' must be a non-empty string"
            if not isinstance(s, str):
                return f"ERROR: 'files[{i}].source' must be a string"
            out_files.append({"path": p, "source": s})
        return {
            "files": out_files,
            "old_name": old_name,
            "new_name": new_name,
            "scope_node": scope_node,
            "source": None,
            "path": None,
        }

    # Single-file
    source = data.get("source")
    path = data.get("path")
    if not isinstance(source, str):
        return "ERROR: missing or invalid 'source' (must be a string)"
    if path is not None and not isinstance(path, str):
        return "ERROR: 'path' must be a string or null"
    return {
        "source": source,
        "old_name": old_name,
        "new_name": new_name,
        "scope_node": scope_node,
        "path": path,
        "files": None,
    }


def _recover_pending_rename_from_artifacts(
    artifacts: list[Artifact] | None,
) -> dict[str, str | None] | None:
    """Return pending_rename from the most recent artifact that has it, or None."""
    if not artifacts:
        return None
    for artifact in reversed(artifacts):
        for part in artifact.parts:
            root = getattr(part, "root", None)
            if isinstance(root, DataPart) and PENDING_RENAME_KEY in root.data:
                payload = root.data[PENDING_RENAME_KEY]
                if (
                    isinstance(payload, dict)
                    and "source" in payload
                    and "old_name" in payload
                    and "new_name" in payload
                ):
                    return {
                        "source": payload.get("source"),
                        "old_name": payload.get("old_name"),
                        "new_name": payload.get("new_name"),
                        "scope_node": payload.get("scope_node"),
                    }
    return None


def _is_confirmation_yes(user_input: str) -> bool:
    """True if user input means proceed (yes, y, proceed)."""
    normalized = user_input.strip().lower()
    return normalized in ("yes", "y", "proceed")


def _is_confirmation_no(user_input: str) -> bool:
    """True if user input means cancel (no, n, cancel)."""
    normalized = user_input.strip().lower()
    return normalized in ("no", "n", "cancel")


def _do_rename(params: dict[str, str | None]) -> str:
    """Run rename via LibCSTEngine. Returns summary and modified source or error."""
    source = params["source"]
    old_name = params["old_name"]
    new_name = params["new_name"]
    scope_node = params["scope_node"]
    # Params are validated by _parse_rename_params before _do_rename is called
    if not (
        isinstance(source, str)
        and isinstance(old_name, str)
        and isinstance(new_name, str)
    ):
        return "ERROR: invalid params (source/old_name/new_name must be strings)"
    try:
        engine = LibCSTEngine(source)
    except Exception as e:
        return f"ERROR: invalid Python syntax: {e}"
    result = engine.rename_symbol(old_name, new_name, scope_node)
    if result.startswith("ERROR:"):
        return result
    modified = engine.to_source()
    return f"{result}{MODIFIED_SOURCE_MARKER}{modified}"


def _success_artifact(
    task_id: str,
    context_id: str,
    result_text: str,
    path: str | None,
    *,
    append: bool = False,
) -> TaskArtifactUpdateEvent:
    """Build artifact with modified_source and path so the client can apply the edit."""
    if MODIFIED_SOURCE_MARKER in result_text:
        summary, _, modified = result_text.partition(MODIFIED_SOURCE_MARKER)
        summary = summary.strip()
    else:
        summary = result_text.strip()
        modified = ""
    data: dict[str, str | None] = {
        "summary": summary,
        "modified_source": modified,
        RENAME_RESULT_KEY: "1",
    }
    if path is not None:
        data["path"] = path
    artifact = Artifact(
        artifact_id=uuid.uuid4().hex,
        name="rename-result",
        description="Refactored source; apply modified_source to path (if given).",
        parts=[
            Part(root=TextPart(text=result_text)),
            Part(root=DataPart(data=data)),
        ],
    )
    return TaskArtifactUpdateEvent(
        task_id=task_id,
        context_id=context_id,
        artifact=artifact,
        append=append,
    )


def _handle_rename_task(user_input: str) -> str:
    """Parse JSON input, run rename via LibCSTEngine, return result text.

    Expected JSON: {"source": "...", "old_name": "...", "new_name": "...",
                    "scope_node": "..." (optional)}.
    Returns summary and modified source, or an error string.
    """
    parsed = _parse_rename_params(user_input)
    if isinstance(parsed, str):
        return parsed
    return _do_rename(parsed)


def _collision_artifact_and_status(
    task_id: str,
    context_id: str,
    collisions: list[CollisionInfo],
    new_name: str,
    params: dict[str, str | None],
) -> tuple[TaskArtifactUpdateEvent, TaskStatusUpdateEvent]:
    """Build artifact (text + pending_rename data) and input_required status."""
    lines = [
        f"Name collision detected: '{new_name}' already exists in this file.",
        "",
        "Conflicting definitions:",
        *[f"  - {c.kind} at {c.location}" for c in collisions],
        "",
    ]
    lines.append("Proceeding would shadow these definitions.")
    lines.append("Confirm? (yes/no)")
    text = "\n".join(lines)
    payload = {
        "source": params["source"],
        "old_name": params["old_name"],
        "new_name": params["new_name"],
        "scope_node": params["scope_node"],
    }
    artifact = Artifact(
        artifact_id=uuid.uuid4().hex,
        name="rename-collision",
        description="Name collision; approval required",
        parts=[
            Part(root=TextPart(text=text)),
            Part(root=DataPart(data={PENDING_RENAME_KEY: payload})),
        ],
    )
    artifact_event = TaskArtifactUpdateEvent(
        task_id=task_id,
        context_id=context_id,
        artifact=artifact,
        append=False,
    )
    status_message = _agent_message("Name collision — approval required")
    status_event = TaskStatusUpdateEvent(
        task_id=task_id,
        context_id=context_id,
        status=TaskStatus(
            state=TaskState.input_required,
            message=status_message,
        ),
        final=False,
    )
    return artifact_event, status_event


class ASTRefactorAgentExecutor(AgentExecutor):
    """A2A executor for rename_symbol: structured JSON in, result message out."""

    async def execute(  # noqa: PLR0911, PLR0912, PLR0915, C901 — resumption, single/multi-file, collision
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Run rename task: check collisions, pause for approval, or run rename."""
        user_input = context.get_user_input()
        task_id = context.task_id
        context_id = context.context_id
        if task_id is None or context_id is None:
            # No task/context to attach; bridge would still get Message not Task
            await event_queue.enqueue_event(
                _agent_message("ERROR: missing task_id or context_id")
            )
            return
        assert task_id is not None  # noqa: S101 — narrow for mypy
        assert context_id is not None  # noqa: S101
        current_task = getattr(context, "current_task", None)

        # Resumption: we were waiting for yes/no
        if (
            current_task is not None
            and current_task.status.state == TaskState.input_required
        ):
            pending = _recover_pending_rename_from_artifacts(current_task.artifacts)
            if pending is not None:
                if _is_confirmation_yes(user_input):
                    result = _do_rename(pending)
                    await event_queue.enqueue_event(
                        _success_artifact(
                            task_id,
                            context_id,
                            result,
                            pending.get("path"),
                        )
                    )
                    await event_queue.enqueue_event(
                        _status_event(task_id, context_id, TaskState.completed, result)
                    )
                    return
                if _is_confirmation_no(user_input):
                    await event_queue.enqueue_event(
                        _status_event(
                            task_id,
                            context_id,
                            TaskState.completed,
                            "Rename canceled.",
                        )
                    )
                    return
                await event_queue.enqueue_event(
                    _status_event(
                        task_id,
                        context_id,
                        TaskState.input_required,
                        "Reply with yes or no to confirm or cancel.",
                        final=False,
                    )
                )
                return

        # Initial request
        if not user_input.strip():
            await event_queue.enqueue_event(
                _status_event(
                    task_id,
                    context_id,
                    TaskState.failed,
                    "ERROR: empty input. Send JSON: "
                    '{"source": "...", "old_name": "...", "new_name": "..."}',
                )
            )
            return

        parsed = _parse_rename_params(user_input)
        if isinstance(parsed, str):
            await event_queue.enqueue_event(
                _status_event(task_id, context_id, TaskState.failed, parsed)
            )
            return

        workspace_list = parsed.get("workspace")
        if isinstance(workspace_list, list) and len(workspace_list) > 0:
            # Impact by trying rename in each file; return artifact per impacted file
            results: list[str] = []
            first_artifact = True
            for file_spec in workspace_list:
                single = {
                    "source": file_spec["source"],
                    "old_name": parsed["old_name"],
                    "new_name": parsed["new_name"],
                    "scope_node": parsed.get("scope_node"),
                }
                result = _do_rename(single)
                if result.startswith("ERROR:"):
                    continue  # Symbol not in this file, skip
                await event_queue.enqueue_event(
                    _success_artifact(
                        task_id,
                        context_id,
                        result,
                        file_spec["path"],
                        append=not first_artifact,
                    )
                )
                first_artifact = False
                if MODIFIED_SOURCE_MARKER in result:
                    summary, _, _ = result.partition(MODIFIED_SOURCE_MARKER)
                    results.append(f"{file_spec['path']}: {summary.strip()}")
                else:
                    results.append(file_spec["path"])
            if not results:
                await event_queue.enqueue_event(
                    _status_event(
                        task_id,
                        context_id,
                        TaskState.failed,
                        "ERROR: no files in workspace reference the symbol "
                        f"'{parsed['old_name']}'",
                    )
                )
                return
            summary_msg = "Renamed in {} file(s):\n{}".format(
                len(results),
                "\n".join(f"  - {r}" for r in results),
            )
            await event_queue.enqueue_event(
                _status_event(task_id, context_id, TaskState.completed, summary_msg)
            )
            return

        files = parsed.get("files")
        if isinstance(files, list) and len(files) > 0:
            # Multi-file rename: one artifact per file, then one summary status
            results: list[str] = []
            for i, file_spec in enumerate(files):
                single = {
                    "source": file_spec["source"],
                    "old_name": parsed["old_name"],
                    "new_name": parsed["new_name"],
                    "scope_node": parsed.get("scope_node"),
                }
                result = _do_rename(single)
                if result.startswith("ERROR:"):
                    await event_queue.enqueue_event(
                        _status_event(
                            task_id,
                            context_id,
                            TaskState.failed,
                            f"{result} (file: {file_spec['path']})",
                        )
                    )
                    return
                await event_queue.enqueue_event(
                    _success_artifact(
                        task_id,
                        context_id,
                        result,
                        file_spec["path"],
                        append=(i > 0),
                    )
                )
                if MODIFIED_SOURCE_MARKER in result:
                    summary, _, _ = result.partition(MODIFIED_SOURCE_MARKER)
                    results.append(f"{file_spec['path']}: {summary.strip()}")
                else:
                    results.append(file_spec["path"])
            summary_msg = "Renamed in {} file(s):\n{}".format(
                len(results),
                "\n".join(f"  - {r}" for r in results),
            )
            await event_queue.enqueue_event(
                _status_event(task_id, context_id, TaskState.completed, summary_msg)
            )
            return

        try:
            engine = LibCSTEngine(parsed["source"])  # type: ignore[arg-type]
        except Exception as e:
            await event_queue.enqueue_event(
                _status_event(
                    task_id,
                    context_id,
                    TaskState.failed,
                    f"ERROR: invalid Python syntax: {e}",
                )
            )
            return

        collisions = engine.check_name_collisions(
            parsed["new_name"],  # type: ignore[arg-type]
            parsed["scope_node"],
        )
        if collisions:
            artifact_ev, status_ev = _collision_artifact_and_status(
                task_id,
                context_id,
                collisions,
                parsed["new_name"],  # type: ignore[arg-type]
                parsed,
            )
            await event_queue.enqueue_event(artifact_ev)
            await event_queue.enqueue_event(status_ev)
            return

        result = _do_rename(parsed)
        await event_queue.enqueue_event(
            _success_artifact(
                task_id,
                context_id,
                result,
                parsed.get("path"),
            )
        )
        await event_queue.enqueue_event(
            _status_event(task_id, context_id, TaskState.completed, result)
        )

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel is not supported."""
        raise NotImplementedError("cancel not supported")
