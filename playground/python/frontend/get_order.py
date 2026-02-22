"""Get order handler — VIOLATION: backend use case placed in frontend.

This module should live in application/use_cases/. Refactoring to enforce
frontend/backend boundary would move it and update imports.
"""

from __future__ import annotations

from playground.python.domain.entities.order import Order


def get_order_handler(_order_id: str) -> Order | None:
    """Frontend handler that fetches an order (duplicates get_order use case)."""
    return None  # Stub; should delegate to application/use_cases/get_order
