from __future__ import annotations

import os
from dataclasses import asdict, is_dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field

from logicfp.domain.models import HandlerRequest
from logicfp import protect


class ReviewRequest(BaseModel):
    product_name: str
    review_text: str
    customer_tier: str = "standard"


class ReviewResult(BaseModel):
    sentiment: str
    summary: str
    risk_level: str
    follow_up_required: bool = False


class LangChainInvokeLike(Protocol):
    def invoke(self, payload: dict[str, Any]) -> Any: ...


class LangChainAsyncInvokeLike(Protocol):
    async def ainvoke(self, payload: dict[str, Any]) -> Any: ...


def _extract_structured_response(result: Any) -> Any:
    if isinstance(result, dict) and "structured_response" in result:
        return result["structured_response"]
    if isinstance(result, BaseModel):
        return result.model_dump()
    if is_dataclass(result):
        return asdict(result)
    return result


def _build_prompt(payload: dict[str, Any]) -> str:
    return (
        "You are reviewing a customer comment.\n"
        f"Product: {payload['product_name']}\n"
        f"Customer tier: {payload['customer_tier']}\n"
        f"Review: {payload['review_text']}\n"
        "Return structured output with sentiment, summary, risk_level, and "
        "follow_up_required."
    )


def build_review_guard(agent: LangChainInvokeLike):
    @protect(input_model=ReviewRequest, output_model=ReviewResult, simple=False)
    def run_review(request: HandlerRequest) -> Any:
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _build_prompt(request.payload),
                    }
                ]
            }
        )
        return _extract_structured_response(result)

    return run_review


def build_async_review_guard(agent: LangChainAsyncInvokeLike):
    @protect(input_model=ReviewRequest, output_model=ReviewResult, simple=False)
    async def run_review(request: HandlerRequest) -> Any:
        result = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _build_prompt(request.payload),
                    }
                ]
            }
        )
        return _extract_structured_response(result)

    return run_review


def build_langchain_agent():
    try:
        from langchain.agents import create_agent
        from langchain.agents.structured_output import ToolStrategy
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Install 'langchain' and your model provider package first. "
            "For example: uv add langchain langchain-openai"
        ) from exc

    model = os.getenv("LANGCHAIN_MODEL", "gpt-5")
    return create_agent(
        model=model,
        tools=[],
        response_format=ToolStrategy(ReviewResult),
    )


def main() -> None:
    agent = build_langchain_agent()
    guarded_review = build_review_guard(agent)
    result = guarded_review(
        payload={
            "product_name": "logicfp",
            "review_text": "Fast setup, but support should confirm the retry policy.",
            "customer_tier": "enterprise",
        }
    )
    print(result)


if __name__ == "__main__":
    main()
