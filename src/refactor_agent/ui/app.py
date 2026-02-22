"""Chainlit chat UI for the AST refactor agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, cast

import chainlit as cl
from chainlit.data import get_data_layer
from langfuse import get_client, propagate_attributes
from pydantic_ai._agent_graph import End, ModelRequestNode

from refactor_agent.observability.langfuse_config import init_langfuse
from refactor_agent.orchestrator import (
    NeedInput,
    OrchestratorDeps,
    create_orchestrator_agent,
    get_chat_agent_instructions,
)
from refactor_agent.schedule import (
    RefactorSchedule,
    execute_schedule,
)

_TRACE_NAME = "chat-agent"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3] / "playground"

# Suggested prompts shown after workspace choice (from docs/testing/README.md).
SUGGESTED_PROMPTS: list[tuple[str, str]] = [
    ("vertical_slice", "Refactor this codebase to a vertical slice structure."),
    (
        "frontend_backend",
        "Enforce frontend/backend boundary: move backend use cases out of the frontend folder.",
    ),
    (
        "reorganize",
        "Create a plan to reorganize the project so the frontend layer does not contain domain logic.",
    ),
]

_LANG_CONFIG: dict[str, dict[str, str]] = {
    "python": {"ext": "*.py", "subdir": "python"},
    # Temporary: NestJS layered playground (revert to "typescript" for original)
    "typescript": {"ext": "*.ts", "subdir": "nestjs-layered-architecture"},
}


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------


def _workspace_dir(language: str) -> Path:
    return _WORKSPACE_ROOT / _LANG_CONFIG[language]["subdir"]


def _scan_files(workspace: Path, ext: str) -> list[Path]:
    if not workspace.exists():
        return []
    return sorted(workspace.rglob(ext))


def _workspace_payload(language: str) -> list[dict[str, str]]:
    """Build workspace list of {path, source} for A2A remote mode."""
    ws = _workspace_dir(language)
    ext = _LANG_CONFIG[language]["ext"]
    files = _scan_files(ws, ext)
    return [
        {"path": str(p.relative_to(ws)), "source": p.read_text(encoding="utf-8")}
        for p in files
    ]


def _a2a_post_sync(base_url: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST JSON-RPC to A2A server (run in thread to avoid blocking)."""
    url = base_url.rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return cast(dict[str, Any], json.loads(resp.read().decode()))


# ---------------------------------------------------------------------------
# Auth (required for persistence and sharing)
# ---------------------------------------------------------------------------


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@cl.password_auth_callback
async def _auth_callback(username: str, password: str) -> cl.User | None:
    """Authenticate with credentials from env or default dev/dev.

    The login form may label the first field as 'Email'; it is still passed
    as username here — use your CHAINLIT_AUTH_USER value (e.g. dev) in that field.
    """
    want_user = _env("CHAINLIT_AUTH_USER", "dev")
    want_pass = _env("CHAINLIT_AUTH_PASSWORD", "dev")
    if (username, password) == (want_user, want_pass):
        return cl.User(identifier=username, metadata={"provider": "credentials"})
    return None


@cl.on_shared_thread_view
async def _on_shared_thread_view(
    thread: cl.types.ThreadDict,  # noqa: ARG001 — signature required by Chainlit
    current_user: cl.User | None,  # noqa: ARG001 — signature required by Chainlit
) -> bool:
    """Allow any authenticated user to view a shared thread."""
    return True


@cl.action_callback("suggested_prompt")
async def _on_suggested_prompt(action: cl.Action) -> None:
    """Run the agent with the prompt from a suggested-prompt button click."""
    payload = action.payload or {}
    prompt = payload.get("prompt")
    language = payload.get("language") or cl.user_session.get("language", "python")
    if not prompt:
        return
    await cl.Message(content=prompt, author="User").send()
    await _run_request(prompt, language)


@cl.action_callback("share_thread")
async def _on_share_thread(action: cl.Action) -> None:
    """Mark the current thread as shared so colleagues can open the share link."""
    data_layer = get_data_layer()
    if not data_layer:
        await cl.Message(
            content="Sharing is not available (no persistence).",
        ).send()
        return
    session = cl.context.session
    thread_id = getattr(session, "thread_id", None)
    if not thread_id:
        await cl.Message(
            content="No active thread to share.",
        ).send()
        return
    thread = await data_layer.get_thread(thread_id)
    if not thread:
        await cl.Message(
            content="Thread not found.",
        ).send()
        return
    raw_meta = thread.get("metadata") or {}
    if isinstance(raw_meta, str):
        raw_meta = json.loads(raw_meta)
    metadata = dict(raw_meta)
    metadata["is_shared"] = True
    await data_layer.update_thread(thread_id, metadata=metadata)
    await cl.Message(
        content="Thread is now shared. Use the share link to let others view it.",
    ).send()
    await action.remove()


# ---------------------------------------------------------------------------
# Chat profiles (modes)
# ---------------------------------------------------------------------------


@cl.set_chat_profiles
async def chat_profiles(user=None):  # noqa: ARG001 — signature required by Chainlit
    return [
        cl.ChatProfile(
            name="Ask",
            markdown_description="Pause for approval on collisions",
            default=True,
        ),
        cl.ChatProfile(
            name="Auto",
            markdown_description="Apply renames without confirmation",
        ),
        cl.ChatProfile(
            name="Plan",
            markdown_description=("Show what would change, don't apply"),
        ),
    ]


# ---------------------------------------------------------------------------
# Conversation start
# ---------------------------------------------------------------------------


@cl.on_chat_start
async def on_chat_start():
    init_langfuse()
    language = await _ask_language()
    cl.user_session.set("language", language)
    cl.user_session.set(
        "environment",
        _env("CHAINLIT_ENVIRONMENT", "dev"),
    )
    cl.user_session.set("message_history", [])
    await _show_workspace(language, show_prompts=True)


@cl.on_chat_resume
async def on_chat_resume(thread: cl.types.ThreadDict) -> None:
    """Restore session from persisted thread and re-show workspace."""
    raw_meta = thread.get("metadata")
    parsed: object = (
        json.loads(raw_meta)
        if isinstance(raw_meta, str)
        else (dict(raw_meta) if raw_meta else {})
    )
    metadata = parsed if isinstance(parsed, dict) else {}
    lang_val = metadata.get("language")
    language = lang_val if isinstance(lang_val, str) else "python"
    if language not in _LANG_CONFIG:
        language = "python"
    cl.user_session.set("language", language)
    env_val = metadata.get("environment")
    env_str = (
        env_val if isinstance(env_val, str) else _env("CHAINLIT_ENVIRONMENT", "dev")
    )
    cl.user_session.set("environment", env_str)
    cl.user_session.set("message_history", [])
    await _show_workspace(language, show_prompts=False)


async def _ask_language() -> str:
    res = await cl.AskActionMessage(
        content="Choose your workspace language:",
        actions=[
            cl.Action(
                name="python",
                payload={"lang": "python"},
                label="Python (playground/python/)",
            ),
            cl.Action(
                name="typescript",
                payload={"lang": "typescript"},
                label="TypeScript (playground/nestjs-layered-architecture/)",
            ),
        ],
    ).send()
    if res is None or res["name"] == "python":
        return "python"
    return "typescript"


async def _show_workspace(language: str, *, show_prompts: bool = True) -> None:
    ws = _workspace_dir(language)
    ext = _LANG_CONFIG[language]["ext"]
    files = _scan_files(ws, ext)
    if files:
        listing = "\n".join(f"- `{f.relative_to(ws)}`" for f in files)
    else:
        listing = "(no files)"
    mode = cl.user_session.get("chat_profile") or "Ask"
    mode_hint = "Ask | Edit (Auto) | Plan — switch via chat profile."
    await cl.Message(
        content=(
            f"**Workspace:** `playground/{_LANG_CONFIG[language]['subdir']}/`\n\n"
            f"**Files:**\n{listing}\n\n"
            f"**Mode:** **{mode}** — {mode_hint}\n\n"
            "Ask me to rename symbols, show file structure, plan a multi-step "
            "refactor, or answer questions about your code."
        ),
        actions=[
            cl.Action(
                name="share_thread",
                label="Share conversation",
                payload={},
            ),
        ],
    ).send()
    if show_prompts:
        await _offer_suggested_prompts(language)


async def _offer_suggested_prompts(language: str) -> None:
    """Show suggested prompt buttons (non-blocking). User can click one or type their own."""
    actions = [
        cl.Action(
            name="suggested_prompt",
            payload={"prompt": prompt, "language": language},
            label=prompt[:48] + "…" if len(prompt) > 48 else prompt,
        )
        for _key, prompt in SUGGESTED_PROMPTS
    ]
    await cl.Message(
        content="**Suggested prompts** (or type your own below):",
        actions=actions,
    ).send()


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------


_TOOL_LABELS: dict[str, str] = {
    "rename_in_workspace": "Renaming `{old_name}` → `{new_name}`",
    "find_references": "Finding references to `{symbol_name}`",
    "remove_declaration": "Removing `{symbol_name}` from `{file_path}`",
    "move_symbol": "Moving `{symbol_name}` to `{target_file}`",
    "format_file": "Formatting `{file_path}`",
    "organize_imports": "Organizing imports in `{file_path}`",
    "show_diagnostics": "Checking diagnostics",
    "list_workspace_files": "Listing workspace files",
    "show_file_skeleton": "Reading `{file_path}` structure",
    "create_refactor_schedule": "Creating refactor schedule for `{goal}`",
}


def _step_label(tool_name: str, args: dict) -> str:  # type: ignore[type-arg]
    template = _TOOL_LABELS.get(tool_name, tool_name)
    try:
        return template.format_map(args)
    except KeyError:
        return tool_name


def _format_schedule(schedule: RefactorSchedule) -> str:
    """Format a RefactorSchedule for display."""
    lines = [f"**Goal:** {schedule.goal}", "", "**Operations:**"]
    for i, op in enumerate(schedule.operations):
        dep = getattr(op, "depends_on", None)
        dep_str = f" (depends on {dep})" if dep else ""
        lines.append(f"{i + 1}. `{op.op}`{dep_str}")
    return "\n".join(lines)


async def _handle_schedule_produced(
    schedule_json: str,
    mode: str,
    deps: OrchestratorDeps,
    *,
    is_partial: bool = False,
) -> None:
    """Display schedule and run executor (with confirmation in Plan/Ask)."""
    try:
        schedule = RefactorSchedule.model_validate_json(schedule_json)
    except Exception:
        return

    if is_partial:
        await cl.Message(
            content="**Partial plan (budget limit reached).** You can still run the "
            "listed operations or refine the goal.",
        ).send()
    await cl.Message(content=_format_schedule(schedule)).send()

    if mode in ("Plan", "Ask"):
        res = await cl.AskUserMessage(
            content="Proceed with execution? Reply **yes** to run the schedule.",
            timeout=120,
        ).send()
        if res is None or (res.get("output") or "").strip().lower() not in (
            "yes",
            "y",
            "go",
        ):
            await cl.Message(content="Execution canceled.").send()
            return

    result = await execute_schedule(schedule, deps)
    if result.success:
        summary = "\n".join(
            f"- {r.op_id or '?'}: {r.op_type} — {r.summary}" for r in result.results
        )
        await cl.Message(
            content=f"**Schedule executed.**\n\n{summary}",
        ).send()
    else:
        if result.error_traceback:
            logging.error(
                "Schedule execution failed: %s\n%s",
                result.error,
                result.error_traceback,
            )
        await cl.Message(
            content=(
                f"**Execution failed:** {result.error}"
                "\n\nCheck the terminal for traceback."
            ),
        ).send()


async def _run_request_remote(content: str, language: str, base_url: str) -> None:
    """Send request to hosted A2A and poll for result; handle input_required with resume."""
    task_id = uuid.uuid4().hex
    context_id = uuid.uuid4().hex
    workspace_list = _workspace_payload(language)
    if not workspace_list:
        workspace_list = [
            {"path": ".keep", "source": "# No workspace files; placeholder for A2A."},
        ]
    payload = {
        "old_name": "",
        "new_name": "",
        "prompt": content,
        "workspace": workspace_list,
        "language": language,
    }
    message_body = {
        "kind": "message",
        "role": "user",
        "messageId": uuid.uuid4().hex,
        "task_id": task_id,
        "context_id": context_id,
        "parts": [{"kind": "text", "text": json.dumps(payload)}],
    }
    body: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": uuid.uuid4().hex,
        "method": "message/send",
        "params": {"message": message_body},
    }

    def _get_task() -> dict[str, Any]:
        get_body = {
            "jsonrpc": "2.0",
            "id": uuid.uuid4().hex,
            "method": "tasks/get",
            "params": {"id": task_id},
        }
        resp = _a2a_post_sync(base_url, get_body)
        if "result" in resp:
            return cast(dict[str, Any], resp["result"])
        return {}

    try:
        while True:
            resp = await asyncio.to_thread(_a2a_post_sync, base_url, body)
            if "error" in resp:
                err = resp["error"]
                msg = err.get("message", json.dumps(err))
                await cl.Message(content=f"A2A error: {msg}").send()
                return
            await asyncio.sleep(1.0)
            task = await asyncio.to_thread(_get_task)
            status = task.get("status") or {}
            state = status.get("state")
            msg_parts = status.get("message", {}).get("parts") or []
            msg_text = ""
            for p in msg_parts:
                if isinstance(p, dict) and "text" in p:
                    msg_text = p["text"]
                    break
            if state == "completed":
                await cl.Message(content=msg_text or "Done.").send()
                return
            if state == "failed":
                await cl.Message(content=msg_text or "Task failed.").send()
                return
            if state == "input_required":
                await cl.Message(content=msg_text or "Input required.").send()
                res = await cl.AskUserMessage(
                    content="Reply to the agent (or type 'cancel' to stop):",
                    timeout=120,
                ).send()
                if res is None:
                    await cl.Message(content="Canceled.").send()
                    return
                reply = (res.get("output") or "").strip() or "cancel"
                message_body = {
                    "kind": "message",
                    "role": "user",
                    "messageId": uuid.uuid4().hex,
                    "task_id": task_id,
                    "context_id": context_id,
                    "parts": [{"kind": "text", "text": reply}],
                }
                body = {
                    "jsonrpc": "2.0",
                    "id": uuid.uuid4().hex,
                    "method": "message/send",
                    "params": {"message": message_body},
                }
                continue
            await asyncio.sleep(1.5)
    except urllib.error.URLError as e:
        logging.exception("A2A request failed")
        await cl.Message(
            content=f"Could not reach A2A server: {e}\n\nCheck REFACTOR_AGENT_A2A_URL.",
        ).send()
    except Exception as exc:
        logging.exception("Remote request failed")
        await cl.Message(
            content=f"Something went wrong: {exc}\n\nCheck the terminal for traceback.",
        ).send()


async def _run_request(content: str, language: str) -> None:
    """Run the orchestrator agent with the given message content."""
    a2a_url = _env("REFACTOR_AGENT_A2A_URL")
    if a2a_url:
        await _run_request_remote(content, language, a2a_url)
        return
    history = cl.user_session.get("message_history") or []
    mode = cl.user_session.get("chat_profile") or "Ask"

    async def get_user_input(need: NeedInput) -> str:
        res = await cl.AskUserMessage(
            content=need.message,
            timeout=60,
        ).send()
        if res is None:
            return "cancel"
        return (res.get("output") or "").strip()

    schedule_output_ref: list[str] = []
    schedule_partial_ref: list[bool] = []
    deps = OrchestratorDeps(
        language=language,
        workspace=_workspace_dir(language),
        mode=mode,
        file_ext=_LANG_CONFIG[language]["ext"],
        get_user_input=get_user_input,
        schedule_output_ref=schedule_output_ref,
        schedule_partial_ref=schedule_partial_ref,
    )

    langfuse = get_client()
    session_id = str(cl.user_session.get("id", ""))

    try:
        instructions = await get_chat_agent_instructions(deps)
        agent = create_orchestrator_agent(instructions_override=instructions)
        with (
            langfuse.start_as_current_observation(
                as_type="agent",
                name=_TRACE_NAME,
                input=content,
            ) as root_observation,
            propagate_attributes(session_id=session_id),
        ):
            async with agent.iter(
                content,
                deps=deps,
                message_history=history,
            ) as run:
                node = run.next_node
                while not isinstance(node, End):
                    next_node = await run.next(node)
                    if isinstance(node, ModelRequestNode):
                        await _show_tool_steps(run)
                    node = next_node

                result = run.result
                if result is not None:
                    root_observation.update(output=result.output)
                    await cl.Message(content=result.output).send()
                cl.user_session.set(
                    "message_history",
                    run.all_messages(),
                )

                if schedule_output_ref:
                    is_partial = bool(
                        schedule_partial_ref
                        and len(schedule_partial_ref) == len(schedule_output_ref)
                        and schedule_partial_ref[-1]
                    )
                    await _handle_schedule_produced(
                        schedule_output_ref[-1],
                        mode,
                        deps,
                        is_partial=is_partial,
                    )
    except Exception as exc:
        logging.exception("Request failed")
        await cl.Message(
            content=f"Something went wrong: {exc}\n\nCheck the terminal for full traceback.",
        ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    language = cl.user_session.get("language")
    if not language or language not in _LANG_CONFIG:
        await cl.Message(
            content="No active workspace. Restart.",
        ).send()
        return
    await _run_request(message.content, language)


async def _show_tool_steps(run: Any) -> None:
    msgs = run.all_messages()
    if not msgs:
        return
    last = msgs[-1]
    for part in getattr(last, "parts", []):
        if type(part).__name__ == "ToolCallPart":
            args = part.args if isinstance(part.args, dict) else {}
            label = _step_label(part.tool_name, args)
            async with cl.Step(name=label) as step:
                step.output = ""
