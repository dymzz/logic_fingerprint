from __future__ import annotations

from pydantic import BaseModel, Field

from logic_fingerprint.domain.models import HandlerRequest, HandlerResponse
from logic_fingerprint.handler_registry import HandlerRegistry


class InventoryLookupInput(BaseModel):
    sku: str
    warehouse: str = "main"


class InventoryLookupOutput(BaseModel):
    sku: str
    warehouse: str
    available: bool
    quantity: int


class OrderQuoteInput(BaseModel):
    order_id: str
    items: list[int] = Field(default_factory=list)


class OrderQuoteOutput(BaseModel):
    order_id: str
    item_count: int
    total: int


def _inventory_lookup(request: HandlerRequest) -> HandlerResponse:
    sku = request.payload["sku"]
    warehouse = request.payload["warehouse"]
    quantity = 24 if sku.startswith("SKU-") else 0
    return HandlerResponse(
        ok=True,
        data={
            "sku": sku,
            "warehouse": warehouse,
            "available": quantity > 0,
            "quantity": quantity,
        },
    )


async def _order_quote(request: HandlerRequest) -> HandlerResponse:
    order_id = request.payload["order_id"]
    items = request.payload.get("items", [])
    return HandlerResponse(
        ok=True,
        data={
            "order_id": order_id,
            "item_count": len(items),
            "total": sum(items),
        },
    )


def register_handlers(handler_registry: HandlerRegistry) -> None:
    handler_registry.register(
        "inventory_lookup",
        _inventory_lookup,
        input_model=InventoryLookupInput,
        output_model=InventoryLookupOutput,
    )
    handler_registry.register(
        "order_quote",
        _order_quote,
        input_model=OrderQuoteInput,
        output_model=OrderQuoteOutput,
    )
