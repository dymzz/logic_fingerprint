from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from examples.config_support import load_example_section, read_example_str
from pydantic import BaseModel, Field

from logicfp.domain.models import HandlerRequest, HandlerResponse
from logicfp.handler_registry import HandlerRegistry


@dataclass(slots=True)
class OpenClawSettings:
    gateway_url: str = "ws://127.0.0.1:18789"
    agent_id: str = "main"
    main_key: str = "main"
    session_prefix: str = "agent"
    channel: str = "acp"
    remote_token_env: str = "OPENCLAW_GATEWAY_TOKEN"


def load_settings() -> OpenClawSettings:
    section = load_example_section("openclaw")
    return OpenClawSettings(
        gateway_url=read_example_str(
            "OPENCLAW_GATEWAY_URL",
            "gateway_url",
            "ws://127.0.0.1:18789",
            section_values=section,
        ),
        agent_id=read_example_str(
            "OPENCLAW_AGENT_ID",
            "agent_id",
            "main",
            section_values=section,
        ),
        main_key=read_example_str(
            "OPENCLAW_MAIN_KEY",
            "main_key",
            "main",
            section_values=section,
        ),
        session_prefix=read_example_str(
            "OPENCLAW_SESSION_PREFIX",
            "session_prefix",
            "agent",
            section_values=section,
        ),
        channel=read_example_str(
            "OPENCLAW_CHANNEL",
            "channel",
            "acp",
            section_values=section,
        ),
        remote_token_env=read_example_str(
            "OPENCLAW_REMOTE_TOKEN_ENV",
            "remote_token_env",
            "OPENCLAW_GATEWAY_TOKEN",
            section_values=section,
        ),
    )


class OpenClawAgentTurnInput(BaseModel):
    conversation_id: str = "main"
    user_text: str
    attachments: list[str] = Field(default_factory=list)


class OpenClawAgentTurnOutput(BaseModel):
    gateway_url: str
    session_key: str
    channel: str
    accepted: bool
    payload: dict[str, Any]


class OpenClawToolDispatchInput(BaseModel):
    conversation_id: str = "main"
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class OpenClawToolDispatchOutput(BaseModel):
    gateway_url: str
    session_key: str
    tool_name: str
    dispatched: bool
    payload: dict[str, Any]


@dataclass(slots=True)
class OpenClawGatewayService:
    settings: OpenClawSettings

    def session_key(self, conversation_id: str | None) -> str:
        effective_key = conversation_id or self.settings.main_key
        return f"{self.settings.session_prefix}:{self.settings.agent_id}:{effective_key}"

    def prepare_agent_turn(
        self,
        *,
        conversation_id: str,
        user_text: str,
        attachments: list[str],
    ) -> dict[str, Any]:
        return {
            "gateway_url": self.settings.gateway_url,
            "session_key": self.session_key(conversation_id),
            "channel": self.settings.channel,
            "accepted": True,
            "payload": {
                "text": user_text,
                "attachments": attachments,
                "auth_env": self.settings.remote_token_env,
            },
        }

    async def dispatch_tool(
        self,
        *,
        conversation_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "gateway_url": self.settings.gateway_url,
            "session_key": self.session_key(conversation_id),
            "tool_name": tool_name,
            "dispatched": True,
            "payload": {
                "arguments": arguments,
                "auth_env": self.settings.remote_token_env,
            },
        }


def register_handlers(handler_registry: HandlerRegistry) -> None:
    settings = load_settings()
    gateway = OpenClawGatewayService(settings=settings)

    def openclaw_agent_turn(request: HandlerRequest) -> HandlerResponse:
        result = gateway.prepare_agent_turn(
            conversation_id=request.payload["conversation_id"],
            user_text=request.payload["user_text"],
            attachments=request.payload.get("attachments", []),
        )
        return HandlerResponse(ok=True, data=result)

    async def openclaw_tool_dispatch(request: HandlerRequest) -> HandlerResponse:
        result = await gateway.dispatch_tool(
            conversation_id=request.payload["conversation_id"],
            tool_name=request.payload["tool_name"],
            arguments=request.payload.get("arguments", {}),
        )
        return HandlerResponse(ok=True, data=result)

    handler_registry.register(
        "openclaw_agent_turn",
        openclaw_agent_turn,
        input_model=OpenClawAgentTurnInput,
        output_model=OpenClawAgentTurnOutput,
    )
    handler_registry.register(
        "openclaw_tool_dispatch",
        openclaw_tool_dispatch,
        input_model=OpenClawToolDispatchInput,
        output_model=OpenClawToolDispatchOutput,
    )
