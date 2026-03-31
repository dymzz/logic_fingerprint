from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PricingService:
    currency: str
    default_discount_rate: float

    async def quote(self, order_id: str, items: list[int]) -> dict[str, str | int | float]:
        subtotal = sum(items)
        discount = round(subtotal * self.default_discount_rate, 2)
        total = round(subtotal - discount, 2)
        return {
            "order_id": order_id,
            "currency": self.currency,
            "item_count": len(items),
            "subtotal": subtotal,
            "discount": discount,
            "total": total,
        }
