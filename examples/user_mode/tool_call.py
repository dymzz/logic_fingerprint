from __future__ import annotations

from pydantic import BaseModel, Field

from logicfp import create_protector
from logicfp.domain.models import HandlerRequest


class QuoteToolInput(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    customer_tier: str = "standard"


class QuoteToolOutput(BaseModel):
    sku: str
    quantity: int
    unit_price: float
    total_price: float


tool_protector = create_protector(
    instance_id="tool-quote",
    default_source="tool_call",
)


@tool_protector.protect(
    input_model=QuoteToolInput,
    output_model=QuoteToolOutput,
    simple=False,
)
def quote_tool(request: HandlerRequest) -> dict[str, float | int | str]:
    payload = request.payload
    tier_discount = {"enterprise": 0.85, "pro": 0.92}.get(payload["customer_tier"], 1.0)
    unit_price = round(199.0 * tier_discount, 2)
    return {
        "sku": payload["sku"],
        "quantity": payload["quantity"],
        "unit_price": unit_price,
        "total_price": round(unit_price * payload["quantity"], 2),
    }


def main() -> None:
    result = quote_tool(
        payload={
            "sku": "logicfp-enterprise",
            "quantity": 3,
            "customer_tier": "enterprise",
        }
    )
    print(result)


if __name__ == "__main__":
    main()
