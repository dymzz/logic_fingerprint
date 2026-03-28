import pytest

pytest.importorskip("pydantic")
from logic_fingerprint.runtime import build_runtime

def test_runtime_contains_registered_handlers():
    runtime = build_runtime()
    names = runtime.handler_registry.names()
    assert "echo_payload" in names
    assert "sum_numbers" in names
    assert "async_echo_payload" in names
