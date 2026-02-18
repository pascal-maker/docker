"""A2A AgentExecutor: single refactor task type (rename_symbol) using LibCSTEngine."""

from __future__ import annotations

import json
import uuid

# RequestContext and EventQueue used in method signatures at runtime
from a2a.server.agent_execution import AgentExecutor, RequestContext  # noqa: TC002
from a2a.server.events import EventQueue  # noqa: TC002
from a2a.types import Message, Part, Role, TextPart

from document_structuring_agent.ast_refactor.engine import LibCSTEngine


def _agent_message(text: str) -> Message:
    """Build an A2A Message with role=agent and a single text part."""
    return Message(
        message_id=uuid.uuid4().hex,
        role=Role.agent,
        parts=[Part(root=TextPart(text=text))],
    )


def _handle_rename_task(user_input: str) -> str:  # noqa: PLR0911 — multiple error paths
    """Parse JSON input, run rename via LibCSTEngine, return result text.

    Expected JSON: {"source": "...", "old_name": "...", "new_name": "...",
                    "scope_node": "..." (optional)}.
    Returns summary and modified source, or an error string.
    """
    try:
        data = json.loads(user_input)
    except json.JSONDecodeError as e:
        return f"ERROR: invalid JSON: {e}"

    source = data.get("source")
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    scope_node = data.get("scope_node")

    if not isinstance(source, str):
        return "ERROR: missing or invalid 'source' (must be a string)"
    if not isinstance(old_name, str):
        return "ERROR: missing or invalid 'old_name' (must be a string)"
    if not isinstance(new_name, str):
        return "ERROR: missing or invalid 'new_name' (must be a string)"
    if scope_node is not None and not isinstance(scope_node, str):
        return "ERROR: 'scope_node' must be a string or null"

    try:
        engine = LibCSTEngine(source)
    except Exception as e:
        return f"ERROR: invalid Python syntax: {e}"

    result = engine.rename_symbol(old_name, new_name, scope_node)
    if result.startswith("ERROR:"):
        return result

    modified = engine.to_source()
    return f"{result}\n\n--- Modified source ---\n{modified}"


class ASTRefactorAgentExecutor(AgentExecutor):
    """A2A executor for rename_symbol: structured JSON in, result message out."""

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Run rename task from context user input and enqueue agent message."""
        user_input = context.get_user_input()
        if not user_input.strip():
            await event_queue.enqueue_event(
                _agent_message(
                    "ERROR: empty input. Send JSON: "
                    '{"source": "...", "old_name": "...", "new_name": "..."}'
                )
            )
            return

        result = _handle_rename_task(user_input)
        await event_queue.enqueue_event(_agent_message(result))

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel is not supported."""
        raise NotImplementedError("cancel not supported")
