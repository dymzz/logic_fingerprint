from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from logicfp.domain.models import HandlerRequest
from logicfp.runtime import build_production_runtime


def test_openclaw_registrar_loads_and_executes(monkeypatch, tmp_path: Path):
    workspace = tmp_path
    config_dir = workspace / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        """
openclaw:
  gateway_url: wss://gateway.example.com:18789
  agent_id: support
  main_key: main
  session_prefix: agent
  channel: acp
  remote_token_env: OPENCLAW_GATEWAY_TOKEN
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    monkeypatch.chdir(workspace)
    monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)
    monkeypatch.delenv("OPENCLAW_GATEWAY_URL", raising=False)
    monkeypatch.delenv("OPENCLAW_AGENT_ID", raising=False)
    monkeypatch.delenv("OPENCLAW_MAIN_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_SESSION_PREFIX", raising=False)
    monkeypatch.delenv("OPENCLAW_CHANNEL", raising=False)
    monkeypatch.delenv("OPENCLAW_REMOTE_TOKEN_ENV", raising=False)

    runtime = build_production_runtime(
        handler_registrars=("examples.openclaw.register_handlers",),
    )

    turn_outcome = runtime.middleware.execute_handler(
        "openclaw_agent_turn",
        request=HandlerRequest(
            payload={
                "conversation_id": "ticket-42",
                "user_text": "Please summarize the outage status.",
                "attachments": ["incident.md"],
            }
        ),
    )
    tool_outcome = asyncio.run(
        runtime.middleware.execute_handler_async(
            "openclaw_tool_dispatch",
            request=HandlerRequest(
                payload={
                    "conversation_id": "ticket-42",
                    "tool_name": "fetch_incident_context",
                    "arguments": {"incident_id": "INC-42"},
                }
            ),
        )
    )

    assert runtime.handler_registry.names() == [
        "openclaw_agent_turn",
        "openclaw_tool_dispatch",
    ]
    assert turn_outcome.succeeded is True
    assert turn_outcome.result.data["gateway_url"] == "wss://gateway.example.com:18789"
    assert turn_outcome.result.data["session_key"] == "agent:support:ticket-42"
    assert tool_outcome.succeeded is True
    assert tool_outcome.result.data["tool_name"] == "fetch_incident_context"
    assert tool_outcome.result.data["payload"]["auth_env"] == "OPENCLAW_GATEWAY_TOKEN"
