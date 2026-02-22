"""Run the orchestrator and detect NeedInput from tool returns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic_ai._agent_graph import End

from refactor_agent.orchestrator.deps import (  # noqa: TC001 — NeedInput at runtime
    NeedInput,
    is_need_input_result,
    parse_need_input_result,
)

if TYPE_CHECKING:
    from pydantic_ai import Agent

    from refactor_agent.orchestrator.deps import OrchestratorDeps


@dataclass
class FinalOutput:
    """Orchestrator run completed with a final text output."""

    output: str


@dataclass
class NeedInputResult:
    """Orchestrator run paused; need user input to resume."""

    need_input: NeedInput
    run_state: RunState


RunState = list[Any]  # message_history for resume; list[ModelMessage]

OrchestratorResult = FinalOutput | NeedInputResult


def _last_tool_return_content(messages: list[Any]) -> str | None:
    """Extract the content of the most recent tool return from message history."""
    for msg in reversed(messages):
        parts = getattr(msg, "parts", [])
        for part in reversed(parts):
            if type(part).__name__ in ("ToolReturnPart", "BuiltinToolReturnPart"):
                content = getattr(part, "content", None)
                if isinstance(content, str):
                    return content
    return None


async def run_orchestrator(
    agent: Agent[OrchestratorDeps, str],
    deps: OrchestratorDeps,
    user_message: str,
    message_history: RunState | None = None,
) -> tuple[OrchestratorResult, RunState]:
    """Run the orchestrator until completion or NeedInput.

    When deps.get_user_input is None (A2A), tool returns are inspected for
    the NeedInput marker; if found, returns NeedInputResult and run_state for
    resume. When get_user_input is set (Chainlit), tools block on input and
    this runner will not see the marker (tools return normal strings).

    Returns:
        (result, run_state): result is FinalOutput or NeedInputResult;
        run_state is message_history to pass to the next run for resume.
    """
    history: RunState = list(message_history) if message_history else []
    history_len = len(history)
    async with agent.iter(
        user_message,
        deps=deps,
        message_history=history,
    ) as run:
        node = run.next_node
        while not isinstance(node, End):
            next_node = await run.next(node)
            if deps.get_user_input is None:
                new_messages = run.all_messages()[history_len:]
                content = _last_tool_return_content(new_messages)
                if content and is_need_input_result(content):
                    parsed = parse_need_input_result(content)
                    if parsed is not None:
                        return (
                            NeedInputResult(
                                need_input=parsed,
                                run_state=run.all_messages(),
                            ),
                            run.all_messages(),
                        )
            node = next_node
        out = run.result.output if run.result else ""
        return FinalOutput(output=out), run.all_messages()
