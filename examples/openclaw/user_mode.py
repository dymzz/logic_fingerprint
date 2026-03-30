from __future__ import annotations

import os
from typing import Any, Protocol

from pydantic import BaseModel, Field

from logicfp import protect
from logicfp.domain.models import HandlerRequest


class TaskDispatchInput(BaseModel):
    session_id: str
    instruction: str
    channel: str = "api"
    max_steps: int = Field(default=10, gt=0, le=50)


class TaskDispatchOutput(BaseModel):
    session_id: str
    status: str
    steps_used: int
    result_text: str
    tool_calls: list[str] = Field(default_factory=list)


class OpenClawAgentLike(Protocol):
    def run(self, *, session_id: str, instruction: str, max_steps: int) -> Any: ...


class OpenClawAsyncAgentLike(Protocol):
    async def arun(self, *, session_id: str, instruction: str, max_steps: int) -> Any: ...


def _normalize_agent_result(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return {
            "session_id": raw.get("session_id", ""),
            "status": raw.get("status", "completed"),
            "steps_used": raw.get("steps_used", 0),
            "result_text": raw.get("result_text", ""),
            "tool_calls": raw.get("tool_calls", []),
        }
    if isinstance(raw, BaseModel):
        return raw.model_dump()
    return {"session_id": "", "status": "unknown", "steps_used": 0, "result_text": str(raw), "tool_calls": []}


def build_task_guard(agent: OpenClawAgentLike):
    @protect(input_model=TaskDispatchInput, output_model=TaskDispatchOutput, simple=False)
    def dispatch_task(request: HandlerRequest) -> Any:
        payload = request.payload
        result = agent.run(
            session_id=payload["session_id"],
            instruction=payload["instruction"],
            max_steps=payload.get("max_steps", 10),
        )
        return _normalize_agent_result(result)

    return dispatch_task


def build_async_task_guard(agent: OpenClawAsyncAgentLike):
    @protect(input_model=TaskDispatchInput, output_model=TaskDispatchOutput, simple=False)
    async def dispatch_task(request: HandlerRequest) -> Any:
        payload = request.payload
        result = await agent.arun(
            session_id=payload["session_id"],
            instruction=payload["instruction"],
            max_steps=payload.get("max_steps", 10),
        )
        return _normalize_agent_result(result)

    return dispatch_task


def build_openclaw_agent():
    try:
        from openclaw import Agent
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Install 'openclaw' first. "
            "For example: uv add openclaw"
        ) from exc

    agent_id = os.getenv("OPENCLAW_AGENT_ID", "default")
    return Agent(agent_id=agent_id)


def main() -> None:
    agent = build_openclaw_agent()
    guarded_task = build_task_guard(agent)
    result = guarded_task(
        payload={
            "session_id": "sess-001",
            "instruction": "Summarize the latest deployment logs and flag any anomalies.",
            "channel": "api",
            "max_steps": 5,
        }
    )
    print(result)


if __name__ == "__main__":
    main()
