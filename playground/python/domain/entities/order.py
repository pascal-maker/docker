"""Order entity."""

from __future__ import annotations

from playground.python.domain.value_objects.money import Money
from playground.python.domain.value_objects.order_id import OrderId


class Order:
    """Domain entity: an order with id and total amount."""

    def __init__(self, order_id: OrderId, total: Money) -> None:
        self.order_id = order_id
        self.total = total
