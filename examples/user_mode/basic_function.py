from __future__ import annotations

from pydantic import BaseModel

from logicfp import protect
from logicfp.domain.models import HandlerRequest


class TicketSummaryInput(BaseModel):
    title: str
    body: str


class TicketSummaryOutput(BaseModel):
    category: str
    priority: str
    summary: str


@protect(input_model=TicketSummaryInput, output_model=TicketSummaryOutput, simple=False)
def summarize_ticket(request: HandlerRequest) -> dict[str, str]:
    payload = request.payload
    body = payload["body"].strip()
    summary = body[:60] + ("..." if len(body) > 60 else "")
    priority = "high" if "outage" in body.lower() or "urgent" in body.lower() else "normal"
    return {
        "category": "support_ticket",
        "priority": priority,
        "summary": f"{payload['title']}: {summary}",
    }


def main() -> None:
    result = summarize_ticket(
        payload={
            "title": "Production login failure",
            "body": "Urgent outage reported by multiple enterprise tenants.",
        }
    )
    print(result)


if __name__ == "__main__":
    main()
