"""Tests for RefactorSchedule and RefactorOperation models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from refactor_agent.schedule.models import (
    RefactorSchedule,
)


def test_refactor_schedule_parses_fixture() -> None:
    """Fixture JSON parses into RefactorSchedule with all operation variants."""
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "refactor_schedule.json"
    with open(fixture_path) as f:
        data = json.load(f)
    schedule = RefactorSchedule.model_validate(data)
    assert schedule.goal
    assert len(schedule.operations) == 2
    op1, op2 = schedule.operations
    assert op1.op == "move_symbol"
    assert op1.source_file == "frontend/get_order.py"
    assert op1.symbol_name == "get_order_handler"
    assert op2.op == "organize_imports"
    assert op2.depends_on == ["op1"]


def test_refactor_schedule_roundtrip_json() -> None:
    """RefactorSchedule round-trips through model_dump_json and model_validate_json."""
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "refactor_schedule.json"
    with open(fixture_path) as f:
        raw = f.read()
    schedule = RefactorSchedule.model_validate_json(raw)
    out = schedule.model_dump_json()
    again = RefactorSchedule.model_validate_json(out)
    assert again.goal == schedule.goal
    assert len(again.operations) == len(schedule.operations)
