from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from examples.config_support import (
    load_example_section,
    read_example_float,
    read_example_int,
    read_example_str,
)
from logic_fingerprint.domain.models import HandlerRequest, HandlerResponse
from logic_fingerprint.handler_registry import HandlerRegistry


@dataclass(slots=True)
class ExampleServiceSettings:
    base_stock: int = 24
    discount_rate: float = 0.10
    tax_rate: float = 0.06
    currency: str = "CNY"


def load_example_service_settings() -> ExampleServiceSettings:
    section = load_example_section("example_services")
    return ExampleServiceSettings(
        base_stock=read_example_int(
            "EXAMPLE_BASE_STOCK",
            "base_stock",
            24,
            section_values=section,
        ),
        discount_rate=read_example_float(
            "EXAMPLE_DISCOUNT_RATE",
            "discount_rate",
            0.10,
            section_values=section,
        ),
        tax_rate=read_example_float(
            "EXAMPLE_TAX_RATE",
            "tax_rate",
            0.06,
            section_values=section,
        ),
        currency=read_example_str(
            "EXAMPLE_CURRENCY",
            "currency",
            "CNY",
            section_values=section,
        ),
    )


class InventorySnapshotInput(BaseModel):
    sku: str
    warehouse: str = "main"


class InventorySnapshotOutput(BaseModel):
    sku: str
    warehouse: str
    available: bool
    quantity: int


class ServiceQuoteInput(BaseModel):
    order_id: str
    items: list[int] = Field(default_factory=list)


class ServiceQuoteOutput(BaseModel):
    order_id: str
    currency: str
    subtotal: int
    discount: float
    tax: float
    total: float


@dataclass(slots=True)
class InventoryRepository:
    base_stock: int

    def quantity_for(self, sku: str) -> int:
        if not sku.startswith("SKU-"):
            return 0
        return self.base_stock


@dataclass(slots=True)
class PricingGateway:
    currency: str

    async def quote(self, order_id: str, items: list[int]) -> dict[str, int | str]:
        return {
            "order_id": order_id,
            "currency": self.currency,
            "subtotal": sum(items),
        }


@dataclass(slots=True)
class QuoteService:
    pricing_gateway: PricingGateway
    discount_rate: float
    tax_rate: float

    async def quote(self, order_id: str, items: list[int]) -> dict[str, str | int | float]:
        pricing = await self.pricing_gateway.quote(order_id, items)
        subtotal = int(pricing["subtotal"])
        discount = round(subtotal * self.discount_rate, 2)
        taxed_base = subtotal - discount
        tax = round(taxed_base * self.tax_rate, 2)
        total = round(taxed_base + tax, 2)
        return {
            "order_id": str(pricing["order_id"]),
            "currency": str(pricing["currency"]),
            "subtotal": subtotal,
            "discount": discount,
            "tax": tax,
            "total": total,
        }


def register_handlers(handler_registry: HandlerRegistry) -> None:
    settings = load_example_service_settings()
    inventory_repository = InventoryRepository(base_stock=settings.base_stock)
    quote_service = QuoteService(
        pricing_gateway=PricingGateway(currency=settings.currency),
        discount_rate=settings.discount_rate,
        tax_rate=settings.tax_rate,
    )

    def inventory_snapshot(request: HandlerRequest) -> HandlerResponse:
        sku = request.payload["sku"]
        warehouse = request.payload["warehouse"]
        quantity = inventory_repository.quantity_for(sku)
        return HandlerResponse(
            ok=True,
            data={
                "sku": sku,
                "warehouse": warehouse,
                "available": quantity > 0,
                "quantity": quantity,
            },
        )

    async def order_quote_with_services(request: HandlerRequest) -> HandlerResponse:
        result = await quote_service.quote(
            order_id=request.payload["order_id"],
            items=request.payload.get("items", []),
        )
        return HandlerResponse(ok=True, data=result)

    handler_registry.register(
        "inventory_snapshot",
        inventory_snapshot,
        input_model=InventorySnapshotInput,
        output_model=InventorySnapshotOutput,
    )
    handler_registry.register(
        "order_quote_with_services",
        order_quote_with_services,
        input_model=ServiceQuoteInput,
        output_model=ServiceQuoteOutput,
    )
