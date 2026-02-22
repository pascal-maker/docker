"""Order repository adapter."""

from __future__ import annotations

from playground.python.domain.entities.order import Order
from playground.python.domain.value_objects.order_id import OrderId


class OrderRepository:
    """In-memory order repository (infrastructure adapter)."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def save(self, order: Order) -> None:
        """Persist an order."""
        self._orders[order.order_id.value] = order

    def find_by_id(self, order_id: OrderId) -> Order | None:
        """Find order by id."""
        return self._orders.get(order_id.value)
