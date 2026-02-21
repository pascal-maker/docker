"""Defines greet(); used by caller and extra. Rename greet → greet_user to test MCP."""

from __future__ import annotations


def greet_user(name: str) -> str:
    """Return a greeting for the given name."""
    return f"Hello, {name}!"
