from __future__ import annotations

from pydantic import BaseModel

from logicfp import protect
from logicfp.user_mode import ProtectRuntimeError
from logicfp.domain.models import HandlerRequest


class RefundInput(BaseModel):
    order_id: str
    amount: float


@protect(input_model=RefundInput, simple=True)
def refund_order(request: HandlerRequest) -> dict[str, str]:
    if request.payload["amount"] > 5000:
        raise ValueError("Refund requires manual review.")
    return {"status": "approved", "order_id": request.payload["order_id"]}


def main() -> None:
    try:
        result = refund_order(payload={"order_id": "R-1001", "amount": 6000})
        print(result)
    except ProtectRuntimeError as exc:
        print(
            {
                "code": exc.code,
                "message": str(exc),
                "details": exc.details,
                "context": exc.context,
            }
        )


if __name__ == "__main__":
    main()
