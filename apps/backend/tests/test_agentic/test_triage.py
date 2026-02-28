"""Tests for triage module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from refactor_agent.agentic.triage import (
    TriageError,
    TriageResult,
    _apply_confidence_rounding,
    create_triage_agent,
    run_triage,
)
from refactor_agent.orchestrator.deps import OrchestratorDeps
from refactor_agent.schedule.models import ScopeSpec


def _deps(workspace: Path) -> OrchestratorDeps:
    return OrchestratorDeps(
        language="typescript",
        workspace=workspace,
        mode="Auto",
        file_ext="*.ts",
    )


def test_apply_confidence_rounding_high_confidence_no_change() -> None:
    """High confidence leaves category unchanged."""
    result = TriageResult(
        category="trivial",
        confidence=0.9,
        scope_spec=ScopeSpec(),
    )
    out = _apply_confidence_rounding(result)
    assert out.category == "trivial"


def test_apply_confidence_rounding_low_confidence_trivial_to_structural() -> None:
    """Low confidence trivial rounds up to structural."""
    result = TriageResult(
        category="trivial",
        confidence=0.5,
        scope_spec=ScopeSpec(),
    )
    out = _apply_confidence_rounding(result)
    assert out.category == "structural"


def test_apply_confidence_rounding_low_confidence_structural_to_paradigm() -> None:
    """Low confidence structural rounds up to paradigm_shift."""
    result = TriageResult(
        category="structural",
        confidence=0.5,
        scope_spec=ScopeSpec(),
    )
    out = _apply_confidence_rounding(result)
    assert out.category == "paradigm_shift"


def test_apply_confidence_rounding_paradigm_unchanged() -> None:
    """Paradigm shift stays paradigm shift."""
    result = TriageResult(
        category="paradigm_shift",
        confidence=0.5,
        scope_spec=ScopeSpec(),
    )
    out = _apply_confidence_rounding(result)
    assert out.category == "paradigm_shift"


def test_triage_result_model() -> None:
    """TriageResult serializes with scope_spec."""
    spec = ScopeSpec(
        affected_files=["a.ts"],
        allowed_op_types=["rename"],
        forbidden_op_types=["create_file"],
    )
    result = TriageResult(
        category="structural",
        confidence=0.8,
        scope_spec=spec,
        brief="Move module",
    )
    assert result.category == "structural"
    assert result.scope_spec.affected_files == ["a.ts"]
    assert result.scope_spec.allowed_op_types == ["rename"]


async def test_run_triage_returns_triage_result(tmp_path: Path) -> None:
    """run_triage returns TriageResult with confidence rounding applied."""
    deps = _deps(tmp_path)
    expected = TriageResult(
        category="trivial",
        confidence=0.9,
        scope_spec=ScopeSpec(affected_files=["x.ts"]),
    )

    mock_agent = AsyncMock()
    mock_run = AsyncMock()
    mock_run.output = expected
    mock_agent.run = AsyncMock(return_value=mock_run)

    with patch(
        "refactor_agent.agentic.triage.create_triage_agent",
        return_value=mock_agent,
    ):
        result = await run_triage("rename X to Y", deps)

    assert result.category == "trivial"
    assert result.confidence == 0.9
    assert result.scope_spec.affected_files == ["x.ts"]


async def test_run_triage_applies_confidence_rounding(tmp_path: Path) -> None:
    """run_triage applies rounding when confidence is low."""
    deps = _deps(tmp_path)
    low_conf_trivial = TriageResult(
        category="trivial",
        confidence=0.5,
        scope_spec=ScopeSpec(),
    )

    mock_agent = AsyncMock()
    mock_run = AsyncMock()
    mock_run.output = low_conf_trivial
    mock_agent.run = AsyncMock(return_value=mock_run)

    with patch(
        "refactor_agent.agentic.triage.create_triage_agent",
        return_value=mock_agent,
    ):
        result = await run_triage("rename X", deps)

    assert result.category == "structural"


async def test_run_triage_raises_on_invalid_output(tmp_path: Path) -> None:
    """run_triage raises TriageError when agent returns non-TriageResult."""
    deps = _deps(tmp_path)

    mock_agent = AsyncMock()
    mock_run = AsyncMock()
    mock_run.output = "not a TriageResult"
    mock_agent.run = AsyncMock(return_value=mock_run)

    with patch(
        "refactor_agent.agentic.triage.create_triage_agent",
        return_value=mock_agent,
    ):
        with pytest.raises(TriageError, match="did not return TriageResult"):
            await run_triage("rename X", deps)


def test_create_triage_agent_returns_agent() -> None:
    """create_triage_agent produces agent with output_type TriageResult."""
    agent = create_triage_agent()
    assert agent.output_type is TriageResult
