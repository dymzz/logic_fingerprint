from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class InventoryRepository:
    source_name: str
    stock_offset: int = 0

    def get_quantity(self, sku: str, warehouse: str) -> int:
        base_quantity = 20 if sku.startswith("SKU-") else 0
        if warehouse == "overflow":
            base_quantity += 5
        return max(0, base_quantity + self.stock_offset)
