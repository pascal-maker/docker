"""Money value object."""

from __future__ import annotations


class Money:
    """Value object: amount and currency."""

    def __init__(self, amount: float, currency: str = "USD") -> None:
        self.amount = amount
        self.currency = currency
