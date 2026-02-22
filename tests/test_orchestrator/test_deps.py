"""Tests for orchestrator deps and NeedInput."""

from __future__ import annotations

from refactor_agent.orchestrator.deps import (
    NeedInput,
    is_need_input_result,
    parse_need_input_result,
    serialize_need_input,
)


def test_serialize_and_parse_need_input() -> None:
    """Round-trip NeedInput serialization."""
    need = NeedInput(
        type="rename_collision",
        message="Name collision. Reply yes or no.",
        payload={"old_name": "foo", "new_name": "bar"},
    )
    s = serialize_need_input(need)
    assert is_need_input_result(s)
    parsed = parse_need_input_result(s)
    assert parsed is not None
    assert parsed.type == need.type
    assert parsed.message == need.message
    assert parsed.payload == need.payload


def test_is_need_input_result_false_for_plain_string() -> None:
    """Plain string is not a NeedInput result."""
    assert not is_need_input_result("Rename complete.")
    assert not is_need_input_result("")


def test_parse_need_input_result_invalid_returns_none() -> None:
    """Invalid or truncated content returns None."""
    assert parse_need_input_result("") is None
    assert parse_need_input_result("__NEED_INPUT__\n") is None
    assert parse_need_input_result("__NEED_INPUT__\nnot-json") is None
