from __future__ import annotations

from dataclasses import dataclass

from examples.config_support import (
    load_example_section,
    read_example_float,
    read_example_int,
    read_example_str,
)


@dataclass(slots=True)
class BusinessSettings:
    inventory_source: str = "inventory-db"
    pricing_currency: str = "CNY"
    stock_offset: int = 0
    default_discount_rate: float = 0.05


def load_settings() -> BusinessSettings:
    section = load_example_section("business")
    return BusinessSettings(
        inventory_source=read_example_str(
            "BUSINESS_INVENTORY_SOURCE",
            "inventory_source",
            "inventory-db",
            section_values=section,
        ),
        pricing_currency=read_example_str(
            "BUSINESS_PRICING_CURRENCY",
            "pricing_currency",
            "CNY",
            section_values=section,
        ),
        stock_offset=read_example_int(
            "BUSINESS_STOCK_OFFSET",
            "stock_offset",
            0,
            section_values=section,
        ),
        default_discount_rate=read_example_float(
            "BUSINESS_DEFAULT_DISCOUNT_RATE",
            "default_discount_rate",
            0.05,
            section_values=section,
        ),
    )
