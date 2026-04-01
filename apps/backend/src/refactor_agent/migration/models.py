"""Pydantic models for React class component detection and migration."""

from __future__ import annotations

from pydantic import BaseModel


class ComponentInfo(BaseModel):
    """A single React class component found in the workspace."""

    file_path: str
    component_name: str
    lifecycle_methods: list[str]
    has_state: bool
    has_refs: bool
    line: int


class ClassComponentList(BaseModel):
    """Result of scanning a workspace for React class components."""

    workspace: str
    components: list[ComponentInfo]

    @property
    def count(self) -> int:
        """Total number of detected class components."""
        return len(self.components)
