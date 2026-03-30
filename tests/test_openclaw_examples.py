from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("pydantic")


def test_openclaw_task_guard_wraps_sync_run(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.openclaw.user_mode import build_task_guard

    class FakeAgent:
        def run(self, *, session_id, instruction, max_steps):
            assert session_id == "sess-001"
            assert "deployment" in instruction.lower()
            return {
                "session_id": session_id,
                "status": "completed",
                "steps_used": 3,
                "result_text": "No anomalies found in deployment logs.",
                "tool_calls": ["read_logs", "grep_errors", "summarize"],
            }

    guarded = build_task_guard(FakeAgent())
    result = guarded(
        payload={
            "session_id": "sess-001",
            "instruction": "Summarize the latest deployment logs and flag any anomalies.",
            "channel": "api",
            "max_steps": 5,
        }
    )

    assert result["ok"] is True
    assert result["result"]["session_id"] == "sess-001"
    assert result["result"]["status"] == "completed"
    assert result["result"]["steps_used"] == 3
    assert "read_logs" in result["result"]["tool_calls"]


def test_openclaw_task_guard_wraps_async_arun(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.openclaw.user_mode import build_async_task_guard

    class FakeAsyncAgent:
        async def arun(self, *, session_id, instruction, max_steps):
            assert session_id == "sess-002"
            return {
                "session_id": session_id,
                "status": "partial",
                "steps_used": max_steps,
                "result_text": "Reached step limit while processing.",
                "tool_calls": ["search_docs"],
            }

    guarded = build_async_task_guard(FakeAsyncAgent())
    result = asyncio.run(
        guarded(
            payload={
                "session_id": "sess-002",
                "instruction": "Find all references to billing in the codebase.",
                "channel": "slack",
                "max_steps": 3,
            }
        )
    )

    assert result["ok"] is True
    assert result["result"]["status"] == "partial"
    assert result["result"]["steps_used"] == 3


def test_openclaw_task_guard_rejects_invalid_input(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.openclaw.user_mode import build_task_guard

    class FakeAgent:
        def run(self, *, session_id, instruction, max_steps):
            raise AssertionError("Should not reach here")

    guarded = build_task_guard(FakeAgent())
    result = guarded(
        payload={
            "session_id": "sess-003",
            "instruction": "test",
            "max_steps": -1,
        }
    )

    assert result["ok"] is False
    assert "error" in result


def test_openclaw_task_guard_catches_agent_exception(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.openclaw.user_mode import build_task_guard

    class FakeAgent:
        def run(self, *, session_id, instruction, max_steps):
            raise RuntimeError("OpenClaw agent crashed mid-execution")

    guarded = build_task_guard(FakeAgent())
    result = guarded(
        payload={
            "session_id": "sess-004",
            "instruction": "Run a dangerous operation.",
            "max_steps": 5,
        }
    )

    assert result["ok"] is False
    assert "error" in result
