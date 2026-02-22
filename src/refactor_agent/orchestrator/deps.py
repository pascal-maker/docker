"""Orchestrator dependencies and NeedInput contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

NEED_INPUT_PREFIX = "__NEED_INPUT__"

_MIN_NEED_INPUT_LINES = 2  # prefix line + JSON line


@dataclass
class NeedInput:
    """Request for user input when a tool needs feedback (e.g. rename collision)."""

    type: str  # e.g. "rename_collision"
    message: str
    payload: dict[str, object]  # e.g. old_name, new_name, collisions, hint


@dataclass
class OrchestratorDeps:
    """Dependencies injected into orchestrator tools.

    When get_user_input is set (e.g. Chainlit), tools call it and block.
    When None (A2A), tools return serialized NeedInput and the runner surfaces it.
    """

    language: str
    workspace: Path
    mode: str
    file_ext: str
    get_user_input: Callable[[NeedInput], Awaitable[str]] | None = None


def serialize_need_input(need: NeedInput) -> str:
    """Return a string that both the model and the runner can use.

    Format: NEED_INPUT_PREFIX + newline + JSON + newline + human message.
    Runner detects the prefix and returns NeedInput; model sees the human message.
    """
    data = {
        "type": need.type,
        "message": need.message,
        "payload": need.payload,
    }
    return f"{NEED_INPUT_PREFIX}\n{json.dumps(data)}\n{need.message}"


def is_need_input_result(content: object) -> bool:
    """True if the tool return content is a serialized NeedInput."""
    if isinstance(content, str):
        return content.strip().startswith(NEED_INPUT_PREFIX)
    return False


def parse_need_input_result(content: str) -> NeedInput | None:  # noqa: PLR0911
    """Parse serialized NeedInput from a tool return string. Returns None if invalid."""
    if not content.strip().startswith(NEED_INPUT_PREFIX):
        return None
    lines = content.strip().split("\n")
    if len(lines) < _MIN_NEED_INPUT_LINES:
        return None
    try:
        data = json.loads(lines[1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    t = data.get("type")
    msg = data.get("message")
    payload = data.get("payload")
    if not isinstance(t, str) or not isinstance(msg, str):
        return None
    if not isinstance(payload, dict):
        payload = {}
    return NeedInput(type=t, message=msg, payload=payload)
