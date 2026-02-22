"""Get order use case."""

from __future__ import annotations

from playground.python.domain.entities.order import Order


def get_order(_order_id: str) -> Order | None:
    """Retrieve an order by id (returns None if not found)."""
    return None  # Stub; real impl would use a repository
