"""Product entity."""

from __future__ import annotations

from playground.python.domain.value_objects.money import Money


class Product:
    """Domain entity: a product with name and price."""

    def __init__(self, name: str, price: Money) -> None:
        self.name = name
        self.price = price
