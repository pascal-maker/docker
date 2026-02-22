"""Chainlit chat UI for the AST refactor agent."""

from __future__ import annotations

from pathlib import Path

import chainlit as cl
from langfuse import get_client, propagate_attributes
from pydantic_ai._agent_graph import End, ModelRequestNode

from refactor_agent.observability.langfuse_config import init_langfuse
from refactor_agent.orchestrator import NeedInput, OrchestratorDeps  # noqa: TC001
from refactor_agent.schedule import (
    RefactorSchedule,
    execute_schedule,
)
from refactor_agent.ui.chat_agent import create_chat_agent

_TRACE_NAME = "chat-agent"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3] / "playground"

_LANG_CONFIG: dict[str, dict[str, str]] = {
    "python": {"ext": "*.py", "subdir": "python"},
    "typescript": {"ext": "*.ts", "subdir": "typescript"},
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
    agent = create_chat_agent()
    cl.user_session.set("chat_agent", agent)
    cl.user_session.set("message_history", [])
    await _show_workspace(language)


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
                label="TypeScript (playground/typescript/)",
            ),
        ],
    ).send()
    if res is None or res["name"] == "python":
        return "python"
    return "typescript"


async def _show_workspace(language: str) -> None:
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
            f"**Workspace:** `playground/{language}/`\n\n"
            f"**Files:**\n{listing}\n\n"
            f"**Mode:** **{mode}** — {mode_hint}\n\n"
            "Ask me to rename symbols, show file structure, plan a multi-step "
            "refactor, or answer questions about your code."
        ),
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
) -> None:
    """Display schedule and optionally run executor based on mode."""
    try:
        schedule = RefactorSchedule.model_validate_json(schedule_json)
    except Exception:
        return

    await cl.Message(content=_format_schedule(schedule)).send()

    if mode == "Plan":
        await cl.Message(
            content=(
                "*Plan mode: schedule displayed only. "
                "Switch to Auto or Ask to execute.*"
            ),
        ).send()
        return

    if mode == "Ask":
        res = await cl.AskUserMessage(
            content="Proceed with execution? Reply yes to run the schedule.",
            timeout=60,
        ).send()
        if res is None or (res.get("output") or "").strip().lower() not in (
            "yes",
            "y",
        ):
            await cl.Message(content="Execution canceled.").send()
            return

    result = await execute_schedule(schedule, deps)
    if result.success:
        summary = "\n".join(
            f"- {r.op_id or '?'}: {r.op_type} — {r.summary}"
            for r in result.results
        )
        await cl.Message(
            content=f"**Schedule executed.**\n\n{summary}",
        ).send()
    else:
        await cl.Message(
            content=f"**Execution failed:** {result.error}",
        ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    language = cl.user_session.get("language")
    if not language or language not in _LANG_CONFIG:
        await cl.Message(
            content="No active workspace. Restart.",
        ).send()
        return

    agent = cl.user_session.get("chat_agent")
    if agent is None:
        await cl.Message(content="Agent not initialized. Restart.").send()
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
    deps = OrchestratorDeps(
        language=language,
        workspace=_workspace_dir(language),
        mode=mode,
        file_ext=_LANG_CONFIG[language]["ext"],
        get_user_input=get_user_input,
        schedule_output_ref=schedule_output_ref,
    )

    langfuse = get_client()
    session_id = str(cl.user_session.get("id", ""))

    try:
        with (
            langfuse.start_as_current_observation(
                as_type="agent",
                name=_TRACE_NAME,
                input=message.content,
            ) as root_observation,
            propagate_attributes(session_id=session_id),
        ):
            async with agent.iter(
                message.content,
                deps=deps,
                message_history=history,
            ) as run:
                node = run.next_node
                while not isinstance(node, End):
                    next_node = await run.next(node)
                    if isinstance(node, ModelRequestNode):
                        await _show_tool_steps(run)
                    node = next_node

                root_observation.update(output=run.result.output)
                await cl.Message(content=run.result.output).send()
                cl.user_session.set(
                    "message_history",
                    run.all_messages(),
                )

                if schedule_output_ref:
                    await _handle_schedule_produced(
                        schedule_output_ref[-1],
                        mode,
                        deps,
                    )
    except Exception as exc:
        await cl.Message(
            content=f"Something went wrong: {exc}",
        ).send()


async def _show_tool_steps(run) -> None:
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
