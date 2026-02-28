"""Tests for Layer 1 intent router."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from refactor_agent.agentic.router import RouteResult, create_router_agent, route_intent


def test_route_result_model() -> None:
    """RouteResult serializes correctly."""
    r = RouteResult(intent="refactor", goal="rename X to Y", confidence=0.9)
    assert r.intent == "refactor"
    assert r.goal == "rename X to Y"
    assert r.confidence == 0.9


async def test_route_intent_returns_route_result() -> None:
    """route_intent returns RouteResult from agent."""
    expected = RouteResult(
        intent="refactor",
        goal="move module to feature slice",
        confidence=0.85,
    )

    mock_agent = AsyncMock()
    mock_run = AsyncMock()
    mock_run.output = expected
    mock_agent.run = AsyncMock(return_value=mock_run)

    with patch(
        "refactor_agent.agentic.router.create_router_agent",
        return_value=mock_agent,
    ):
        result = await route_intent("Please move the module to feature slice")

    assert result.intent == "refactor"
    assert result.goal == "move module to feature slice"
    assert result.confidence == 0.85


async def test_route_intent_fallback_on_invalid_output() -> None:
    """route_intent returns general_chat fallback when agent output is invalid."""
    mock_agent = AsyncMock()
    mock_run = AsyncMock()
    mock_run.output = "not a RouteResult"
    mock_agent.run = AsyncMock(return_value=mock_run)

    with patch(
        "refactor_agent.agentic.router.create_router_agent",
        return_value=mock_agent,
    ):
        result = await route_intent("Hello")

    assert result.intent == "general_chat"
    assert result.goal is None
    assert result.confidence == 0.5


def test_create_router_agent_returns_agent() -> None:
    """create_router_agent produces agent with output_type RouteResult."""
    agent = create_router_agent()
    assert agent.output_type is RouteResult
