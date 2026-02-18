"""Defines greet(); used by caller and extra. Rename greet → greet_user to test MCP."""

from __future__ import annotations


def greet(name: str) -> str:
    """Return a greeting for the given name."""
    return f"Hello, {name}!"
