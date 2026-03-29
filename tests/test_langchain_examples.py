from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("pydantic")


def test_langchain_review_guard_wraps_sync_invoke(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.langchain.user_mode import build_review_guard

    class FakeAgent:
        def invoke(self, payload):
            assert "messages" in payload
            return {
                "structured_response": {
                    "sentiment": "positive",
                    "summary": "Strong fit for enterprise rollout.",
                    "risk_level": "low",
                    "follow_up_required": False,
                }
            }

    guarded = build_review_guard(FakeAgent())
    result = guarded(
        payload={
            "product_name": "logicfp",
            "review_text": "Fast setup and stable retries.",
            "customer_tier": "enterprise",
        }
    )

    assert result["ok"] is True
    assert result["result"]["sentiment"] == "positive"
    assert result["result"]["risk_level"] == "low"


def test_langchain_review_guard_wraps_async_ainvoke(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.langchain.user_mode import build_async_review_guard

    class FakeAsyncAgent:
        async def ainvoke(self, payload):
            assert "messages" in payload
            return {
                "structured_response": {
                    "sentiment": "neutral",
                    "summary": "Customer expects clearer escalation rules.",
                    "risk_level": "medium",
                    "follow_up_required": True,
                }
            }

    guarded = build_async_review_guard(FakeAsyncAgent())
    result = asyncio.run(
        guarded(
            payload={
                "product_name": "logicfp",
                "review_text": "Works well, but escalation is unclear.",
                "customer_tier": "pro",
            }
        )
    )

    assert result["ok"] is True
    assert result["result"]["follow_up_required"] is True
    assert result["result"]["risk_level"] == "medium"
