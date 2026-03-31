from __future__ import annotations

from pydantic import BaseModel, Field

from logicfp.domain.models import HandlerRequest, HandlerResponse
from logicfp.handler_registry import HandlerRegistry

from ..repositories import InventoryRepository
from ..services import InventoryService, PricingService
from ..settings import load_settings


class InventoryLookupInput(BaseModel):
    sku: str
    warehouse: str = "main"


class InventoryLookupOutput(BaseModel):
    sku: str
    warehouse: str
    source: str
    available: bool
    quantity: int


class OrderQuoteInput(BaseModel):
    order_id: str
    items: list[int] = Field(default_factory=list)


class OrderQuoteOutput(BaseModel):
    order_id: str
    currency: str
    item_count: int
    subtotal: int
    discount: float
    total: float


def build_inventory_lookup_handler(service: InventoryService):
    def handler(request: HandlerRequest) -> HandlerResponse:
        result = service.lookup(
            sku=request.payload["sku"],
            warehouse=request.payload["warehouse"],
        )
        return HandlerResponse(ok=True, data=result)

    return handler


def build_order_quote_handler(service: PricingService):
    async def handler(request: HandlerRequest) -> HandlerResponse:
        result = await service.quote(
            order_id=request.payload["order_id"],
            items=request.payload.get("items", []),
        )
        return HandlerResponse(ok=True, data=result)

    return handler


def register_handlers(handler_registry: HandlerRegistry) -> None:
    settings = load_settings()

    inventory_repository = InventoryRepository(
        source_name=settings.inventory_source,
        stock_offset=settings.stock_offset,
    )
    inventory_service = InventoryService(repository=inventory_repository)
    pricing_service = PricingService(
        currency=settings.pricing_currency,
        default_discount_rate=settings.default_discount_rate,
    )

    handler_registry.register(
        "inventory_lookup",
        build_inventory_lookup_handler(inventory_service),
        input_model=InventoryLookupInput,
        output_model=InventoryLookupOutput,
    )
    handler_registry.register(
        "order_quote",
        build_order_quote_handler(pricing_service),
        input_model=OrderQuoteInput,
        output_model=OrderQuoteOutput,
    )
