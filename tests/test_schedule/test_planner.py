"""Tests for planner: budget tool, partial extraction, graceful degradation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from refactor_agent.schedule.limits import (
    MAX_PLANNER_LLM_ROUNDS,
    MAX_PLANNER_TOOL_CALLS_PER_RUN,
)
from refactor_agent.schedule.models import RefactorSchedule
from refactor_agent.schedule.planner import (
    PlannerLimitExceededError,
    PlannerRunResult,
    _extract_json_object,
    _last_assistant_text,
    _parse_schedule_from_text,
    _try_partial_on_limit,
)


def _model_response_with_text(content: str) -> object:
    """Build a minimal ModelResponse + TextPart for _last_assistant_text.

    _last_assistant_text checks type(msg).__name__ == "ModelResponse" and
    type(part).__name__ == "TextPart", so we use classes with those names.
    """

    class TextPart:
        def __init__(self, content: str) -> None:
            self.content = content
            self.text = None

    class ModelResponse:
        def __init__(self, parts: list[object]) -> None:
            self.parts = parts

    return ModelResponse(parts=[TextPart(content)])


def test_last_assistant_text_returns_none_for_empty_messages() -> None:
    assert _last_assistant_text([]) is None


def test_last_assistant_text_returns_none_when_no_model_response() -> None:
    class UserMessage:
        def __init__(self) -> None:
            self.parts: list[object] = []

    assert _last_assistant_text([UserMessage()]) is None


def test_last_assistant_text_returns_text_from_last_model_response() -> None:
    msg = _model_response_with_text("Here is the schedule.")
    assert _last_assistant_text([msg]) == "Here is the schedule."


def test_last_assistant_text_skips_empty_text_parts() -> None:
    empty = _model_response_with_text("   ")
    with_text = _model_response_with_text("valid")
    assert _last_assistant_text([empty, with_text]) == "valid"


def test_extract_json_object_plain_object() -> None:
    raw = '  { "goal": "x", "operations": [] }  '
    out = _extract_json_object(raw)
    assert out is not None
    assert "goal" in out
    assert "operations" in out


def test_extract_json_object_strip_markdown_fence() -> None:
    text = '```json\n{"goal": "g", "operations": []}\n```'
    out = _extract_json_object(text)
    assert out == '{"goal": "g", "operations": []}'


def test_extract_json_object_no_brace_returns_none() -> None:
    assert _extract_json_object("no json here") is None


def test_parse_schedule_from_text_valid_json() -> None:
    text = '{"goal": "Refactor.", "operations": []}'
    schedule = _parse_schedule_from_text(text)
    assert schedule is not None
    assert schedule.goal == "Refactor."
    assert schedule.operations == []


def test_parse_schedule_from_text_with_markdown_fence() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "refactor_schedule.json"
    )
    raw = fixture_path.read_text()
    text = "Some reasoning.\n\n```json\n" + raw + "\n```"
    schedule = _parse_schedule_from_text(text)
    assert schedule is not None
    assert "frontend/backend" in schedule.goal
    assert len(schedule.operations) == 2


def test_parse_schedule_from_text_invalid_returns_none() -> None:
    assert _parse_schedule_from_text("not json at all") is None
    assert _parse_schedule_from_text("[]") is None
    # Invalid op type fails validation.
    assert (
        _parse_schedule_from_text('{"goal": "x", "operations": [{"op": "invalid"}]}')
        is None
    )


def test_try_partial_on_limit_returns_result_when_parseable() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "refactor_schedule.json"
    )
    raw = fixture_path.read_text()
    run = MagicMock()
    run.all_messages.return_value = [_model_response_with_text(raw)]
    span = MagicMock()
    over_limit_tools = MAX_PLANNER_TOOL_CALLS_PER_RUN + 1
    over_limit_rounds = MAX_PLANNER_LLM_ROUNDS + 1
    result = _try_partial_on_limit(run, span, over_limit_tools, over_limit_rounds)
    assert isinstance(result, PlannerRunResult)
    assert result.partial is True
    assert result.schedule.goal
    assert len(result.schedule.operations) == 2
    span.update.assert_called_once()


def test_try_partial_on_limit_raises_when_not_parseable() -> None:
    run = MagicMock()
    run.all_messages.return_value = [_model_response_with_text("no schedule here")]
    span = MagicMock()
    over_limit_tools = MAX_PLANNER_TOOL_CALLS_PER_RUN + 1
    over_limit_rounds = MAX_PLANNER_LLM_ROUNDS + 1
    with pytest.raises(PlannerLimitExceededError) as exc_info:
        _try_partial_on_limit(run, span, over_limit_tools, over_limit_rounds)
    assert exc_info.value.tool_calls == over_limit_tools
    assert exc_info.value.llm_rounds == over_limit_rounds


def test_planner_run_result_default_partial_false() -> None:
    schedule = RefactorSchedule(goal="g", operations=[])
    result = PlannerRunResult(schedule=schedule)
    assert result.partial is False
