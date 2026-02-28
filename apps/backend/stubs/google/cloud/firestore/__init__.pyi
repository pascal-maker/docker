"""Minimal stub for google.cloud.firestore (library has no py.typed)."""

from collections.abc import Callable
from typing import Any, TypeVar

from google.cloud.firestore_v1 import Client

F = TypeVar("F", bound=Callable[..., Any])

__all__ = ["Client", "transactional"]

def transactional(to_wrap: F) -> F: ...
