"""Chainlit chat UI for the AST refactor agent."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import chainlit as cl

from refactor_agent.engine.libcst_engine import LibCSTEngine
from refactor_agent.observability.langfuse_config import init_langfuse

if TYPE_CHECKING:
    from refactor_agent.engine.base import CollisionInfo, RefactorEngine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3] / "playground"

_LANG_CONFIG: dict[str, dict[str, str]] = {
    "python": {"ext": "*.py", "subdir": "python"},
}

_RENAME_RE = re.compile(
    r"rename\s+(\w+)\s+to\s+(\w+)"
    r"(?:\s+in\s+(?:scope\s+)?(\w+))?",
    re.IGNORECASE,
)


class _RenameParams(NamedTuple):
    old_name: str
    new_name: str
    scope_node: str | None


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------


def get_engine(language: str, source: str) -> RefactorEngine:
    """Instantiate the refactor engine for *language*.

    Args:
        language: Workspace language (e.g. ``"python"``).
        source: Source code to parse.

    Returns:
        A ``RefactorEngine`` implementation for the requested language.

    Raises:
        NotImplementedError: If the language engine is not yet available.
    """
    if language == "python":
        return LibCSTEngine(source)
    raise NotImplementedError(f"{language} engine not yet available")


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
# Input parsing
# ---------------------------------------------------------------------------


def _parse_rename(text: str) -> _RenameParams | None:
    stripped = text.strip()
    if stripped.startswith("{"):
        return _parse_rename_json(stripped)
    match = _RENAME_RE.search(stripped)
    if match:
        return _RenameParams(
            old_name=match.group(1),
            new_name=match.group(2),
            scope_node=match.group(3),
        )
    return None


def _parse_rename_json(text: str) -> _RenameParams | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    old = data.get("old_name")
    new = data.get("new_name")
    if isinstance(old, str) and isinstance(new, str):
        scope = data.get("scope_node")
        return _RenameParams(
            old_name=old,
            new_name=new,
            scope_node=scope if isinstance(scope, str) else None,
        )
    return None


# ---------------------------------------------------------------------------
# Collision formatting
# ---------------------------------------------------------------------------


def _format_collisions(
    collisions: list[CollisionInfo],
    new_name: str,
    rel_path: str,
) -> str:
    lines = [
        f"**Collision in `{rel_path}`:** `{new_name}` already exists.",
        "",
        "Conflicting definitions:",
        *(f"- {c.kind} at {c.location}" for c in collisions),
        "",
        "Proceeding would shadow these definitions.",
    ]
    return "\n".join(lines)


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
    if language != "python":
        return
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
    ts_dir = _WORKSPACE_ROOT / "typescript"
    if not ts_dir.exists():
        await cl.Message(
            content=(
                "TypeScript playground not set up yet. "
                "Coming soon! Defaulting to Python."
            ),
        ).send()
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
    await cl.Message(
        content=(
            f"**Workspace:** `playground/{language}/`\n\n"
            f"**Files:**\n{listing}\n\n"
            f"**Mode:** {mode}\n\n"
            "Commands:\n"
            "- `rename <old> to <new>`\n"
            "- `rename <old> to <new> in scope <fn>`\n"
            '- JSON: `{"old_name": "…", "new_name": "…"}`'
        ),
    ).send()


# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------


@cl.on_message
async def on_message(message: cl.Message) -> None:
    language = cl.user_session.get("language")
    if not language or language != "python":
        await cl.Message(
            content="No active Python workspace. Restart.",
        ).send()
        return

    params = _parse_rename(message.content)
    if params is None:
        await cl.Message(
            content=(
                "Unrecognized command. Try:\n"
                "- `rename <old> to <new>`\n"
                '- `{"old_name": "…", "new_name": "…"}`'
            ),
        ).send()
        return

    mode = cl.user_session.get("chat_profile") or "Ask"
    await _do_workspace_rename(
        language=language,
        params=params,
        mode=mode,
    )


# ---------------------------------------------------------------------------
# Multi-file rename
# ---------------------------------------------------------------------------


async def _do_workspace_rename(
    *,
    language: str,
    params: _RenameParams,
    mode: str,
) -> None:
    ws = _workspace_dir(language)
    ext = _LANG_CONFIG[language]["ext"]
    files = _scan_files(ws, ext)
    if not files:
        await cl.Message(content="No files in workspace.").send()
        return

    results: list[str] = []
    async with cl.Step(
        name=f"Rename '{params.old_name}' -> '{params.new_name}'",
    ) as parent_step:
        parent_step.input = (
            f"old_name={params.old_name}"
            f", new_name={params.new_name}"
            f", scope_node={params.scope_node}"
        )
        for fp in files:
            outcome = await _rename_in_file(
                file_path=fp,
                workspace=ws,
                language=language,
                params=params,
                mode=mode,
            )
            if outcome is not None:
                results.append(outcome)

        parent_step.output = (
            "\n".join(results) if results else f"No files reference '{params.old_name}'"
        )

    await _send_summary(results, params.old_name, mode)


async def _send_summary(
    results: list[str],
    old_name: str,
    mode: str,
) -> None:
    if results:
        label = "Plan" if mode == "Plan" else "Rename"
        summary = f"**{label} complete** ({len(results)} file(s)):\n" + "\n".join(
            f"- {r}" for r in results
        )
    else:
        summary = f"Symbol `{old_name}` not found in any workspace file."
    await cl.Message(content=summary).send()


# ---------------------------------------------------------------------------
# Single-file rename
# ---------------------------------------------------------------------------


async def _rename_in_file(
    *,
    file_path: Path,
    workspace: Path,
    language: str,
    params: _RenameParams,
    mode: str,
) -> str | None:
    rel = str(file_path.relative_to(workspace))
    source = file_path.read_text(encoding="utf-8")
    try:
        engine = get_engine(language, source)
    except Exception:  # skip unparseable files
        return None

    skip = await _handle_collisions(
        engine=engine,
        new_name=params.new_name,
        scope_node=params.scope_node,
        rel_path=rel,
        mode=mode,
    )
    if skip is not None:
        return skip

    result = engine.rename_symbol(
        params.old_name,
        params.new_name,
        params.scope_node,
    )
    if result.startswith("ERROR:"):
        return None

    if mode == "Plan":
        async with cl.Step(
            name=f"Would rename in {rel}",
        ) as step:
            step.output = result
        return f"[plan] {rel}: {result}"

    file_path.write_text(engine.to_source(), encoding="utf-8")
    async with cl.Step(name=f"Renamed in {rel}") as step:
        step.output = result
    return f"{rel}: {result}"


# ---------------------------------------------------------------------------
# Collision handling
# ---------------------------------------------------------------------------


async def _handle_collisions(
    *,
    engine: RefactorEngine,
    new_name: str,
    scope_node: str | None,
    rel_path: str,
    mode: str,
) -> str | None:
    """Check for name collisions and handle based on mode.

    Returns a skip-reason string if the file should be skipped,
    or ``None`` to proceed with the rename.
    """
    collisions = engine.check_name_collisions(new_name, scope_node)
    if not collisions:
        return None

    text = _format_collisions(collisions, new_name, rel_path)

    if mode == "Plan":
        async with cl.Step(
            name=f"Collision in {rel_path}",
        ) as step:
            step.output = text + "\n(Plan mode: not applied)"
        return f"[collision] {rel_path}: not applied"

    if mode == "Ask":
        res = await cl.AskActionMessage(
            content=text + "\n\nProceed anyway?",
            actions=[
                cl.Action(
                    name="yes",
                    payload={"confirm": True},
                    label="Yes, proceed",
                ),
                cl.Action(
                    name="no",
                    payload={"confirm": False},
                    label="No, skip",
                ),
            ],
        ).send()
        if res is None or res["name"] != "yes":
            async with cl.Step(
                name=f"Skipped {rel_path}",
            ) as step:
                step.output = "User declined collision override"
            return f"[skipped] {rel_path}: collision"

    return None
