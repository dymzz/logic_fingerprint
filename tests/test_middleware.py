import asyncio
import pytest
from logic_fingerprint.core.models import HandlerRequest

pytest.importorskip("pydantic")
from logic_fingerprint.runtime import build_runtime

def test_middleware_autofills_context_for_sync_handler():
    runtime = build_runtime()
    outcome = runtime.middleware.execute_handler("echo_payload", request=HandlerRequest(payload={"hello": "world"}))
    assert outcome.executed is True
    assert outcome.succeeded is True
    assert outcome.result.data["request_id"] is not None
    assert outcome.result.data["trace_id"] is not None
    assert outcome.result.data["source"] == "api"

def test_middleware_validates_input_schema():
    runtime = build_runtime()
    outcome = runtime.middleware.execute_handler("sum_numbers", request=HandlerRequest(payload={"numbers": ["x"]}))
    assert outcome.executed is True
    assert outcome.succeeded is False
    assert outcome.error_code == "ERR_VALIDATION"

def test_middleware_validates_output_schema():
    runtime = build_runtime()
    outcome = runtime.middleware.execute_handler("sum_numbers", request=HandlerRequest(payload={"numbers": [1, 2, 3]}))
    assert outcome.executed is True
    assert outcome.succeeded is True
    assert outcome.result.data["sum"] == 6

def test_middleware_autofills_context_for_async_handler():
    runtime = build_runtime()
    async def run():
        return await runtime.middleware.execute_handler_async("async_echo_payload", request=HandlerRequest(payload={"k": "v"}))
    outcome = asyncio.run(run())
    assert outcome.executed is True
    assert outcome.succeeded is True
    assert outcome.result.data["request_id"] is not None
