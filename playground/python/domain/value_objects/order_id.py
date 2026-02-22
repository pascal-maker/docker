"""OrderId value object."""

from __future__ import annotations


class OrderId:
    """Value object: unique order identifier."""

    def __init__(self, value: str) -> None:
        self.value = value
