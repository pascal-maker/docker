"""Orchestrator dependencies and NeedInput contract."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

NEED_INPUT_PREFIX = "__NEED_INPUT__"

_MIN_NEED_INPUT_LINES = 2  # prefix line + JSON line


class NeedInputPayload(BaseModel):
    """Structured payload for NeedInput (e.g. rename_collision: old_name, new_name)."""

    model_config = ConfigDict(extra="allow")


class PlannerBudgetRef(BaseModel):
    """Mutable ref for planner run budget (tool_calls and llm_rounds)."""

    tool_calls: int = 0
    llm_rounds: int = 0


@dataclass
class NeedInput:
    """Request for user input when a tool needs feedback (e.g. rename collision)."""

    type: str  # e.g. "rename_collision"
    message: str
    payload: NeedInputPayload  # e.g. old_name, new_name, collisions, hint


@dataclass
class OrchestratorDeps:
    """Dependencies injected into orchestrator tools.

    When get_user_input is set (e.g. Chainlit), tools call it and block.
    When None (A2A), tools return serialized NeedInput and the runner surfaces it.
    When schedule_output_ref is set (e.g. Dev UI), create_refactor_schedule
    appends the schedule JSON so the app can run the executor by mode.
    """

    language: str
    workspace: Path
    mode: str
    file_ext: str
    get_user_input: Callable[[NeedInput], Awaitable[str]] | None = None
    schedule_output_ref: list[str] | None = None
    schedule_partial_ref: list[bool] | None = None
    schedule_produced: bool = False
    # Set by run_planner during a planner run; tools read current counts for budget.
    planner_budget_ref: PlannerBudgetRef | None = None


def serialize_need_input(need: NeedInput) -> str:
    """Return a string that both the model and the runner can use.

    Format: NEED_INPUT_PREFIX + newline + JSON + newline + human message.
    Runner detects the prefix and returns NeedInput; model sees the human message.
    """
    data = {
        "type": need.type,
        "message": need.message,
        "payload": need.payload.model_dump(),
    }
    return f"{NEED_INPUT_PREFIX}\n{json.dumps(data)}\n{need.message}"


def is_need_input_result(content: object) -> bool:
    """True if the tool return content is a serialized NeedInput."""
    if isinstance(content, str):
        return content.strip().startswith(NEED_INPUT_PREFIX)
    return False


def parse_need_input_result(content: str) -> NeedInput | None:
    """Parse serialized NeedInput from a tool return string. Returns None if invalid."""
    result: NeedInput | None = None
    stripped = content.strip()
    if stripped.startswith(NEED_INPUT_PREFIX):
        lines = stripped.split("\n")
        if len(lines) >= _MIN_NEED_INPUT_LINES:
            try:
                data = json.loads(lines[1])
                if isinstance(data, dict):
                    t = data.get("type")
                    msg = data.get("message")
                    if isinstance(t, str) and isinstance(msg, str):
                        payload = data.get("payload")
                        payload_dict = payload if isinstance(payload, dict) else {}
                        result = NeedInput(
                            type=t,
                            message=msg,
                            payload=NeedInputPayload.model_validate(payload_dict),
                        )
            except json.JSONDecodeError:
                pass
    return result
