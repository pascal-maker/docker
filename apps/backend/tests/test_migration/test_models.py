"""Tests for migration Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from refactor_agent.migration.models import ClassComponentList, ComponentInfo


def test_component_info_validates_all_fields() -> None:
    """ComponentInfo validates correctly with all fields provided."""
    info = ComponentInfo(
        file_path="/path/to/MyComp.tsx",
        component_name="MyComp",
        lifecycle_methods=["componentDidMount", "render"],
        has_state=True,
        has_refs=False,
        line=10,
    )
    assert info.file_path == "/path/to/MyComp.tsx"
    assert info.component_name == "MyComp"
    assert info.lifecycle_methods == ["componentDidMount", "render"]
    assert info.has_state is True
    assert info.has_refs is False
    assert info.line == 10


def test_component_info_empty_lifecycle_methods() -> None:
    """ComponentInfo with empty lifecycle_methods list is valid."""
    info = ComponentInfo(
        file_path="/path/to/Simple.tsx",
        component_name="Simple",
        lifecycle_methods=[],
        has_state=False,
        has_refs=False,
        line=1,
    )
    assert info.lifecycle_methods == []


def test_class_component_list_count() -> None:
    """ClassComponentList.count returns len(components)."""
    comp1 = ComponentInfo(
        file_path="/a.tsx",
        component_name="A",
        lifecycle_methods=["render"],
        has_state=False,
        has_refs=False,
        line=1,
    )
    comp2 = ComponentInfo(
        file_path="/b.tsx",
        component_name="B",
        lifecycle_methods=["render", "componentDidMount"],
        has_state=True,
        has_refs=False,
        line=5,
    )
    result = ClassComponentList(workspace="/workspace", components=[comp1, comp2])
    assert result.count == 2


def test_class_component_list_empty_count() -> None:
    """ClassComponentList with empty components list returns count == 0."""
    result = ClassComponentList(workspace="/workspace", components=[])
    assert result.count == 0


def test_component_info_rejects_missing_fields() -> None:
    """ComponentInfo rejects construction with missing required fields."""
    with pytest.raises(ValidationError):
        ComponentInfo(  # type: ignore[call-arg]
            file_path="/path/to/MyComp.tsx",
            component_name="MyComp",
            # Missing: lifecycle_methods, has_state, has_refs, line
        )
