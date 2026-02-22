"""Create order use case."""

from __future__ import annotations

from playground.python.domain.entities.order import Order
from playground.python.domain.value_objects.money import Money
from playground.python.domain.value_objects.order_id import OrderId


def create_order(order_id: OrderId, total: Money) -> Order:
    """Create a new order."""
    return Order(order_id=order_id, total=total)
