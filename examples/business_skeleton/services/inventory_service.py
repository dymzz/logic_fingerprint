from __future__ import annotations

from dataclasses import dataclass

from ..repositories import InventoryRepository


@dataclass(slots=True)
class InventoryService:
    repository: InventoryRepository

    def lookup(self, sku: str, warehouse: str) -> dict[str, int | str | bool]:
        quantity = self.repository.get_quantity(sku, warehouse)
        return {
            "sku": sku,
            "warehouse": warehouse,
            "source": self.repository.source_name,
            "available": quantity > 0,
            "quantity": quantity,
        }
