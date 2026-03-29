import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from logic_fingerprint.app_factory import create_app, create_demo_app
from logic_fingerprint.runtime import build_demo_runtime

def test_execute_handler_success_envelope():
    client = TestClient(create_demo_app())
    response = client.post("/execute_handler", json={"handler": "sum_numbers", "payload": {"numbers": [1, 2, 3]}})
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["data"]["sum"] == 6

def test_execute_handler_validation_error_envelope():
    client = TestClient(create_demo_app())
    response = client.post("/execute_handler", json={"handler": "sum_numbers", "payload": {"numbers": ["x"]}})
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "ERR_VALIDATION"
    assert "errors" in body["error"]["details"]

def test_execute_handler_autofills_context():
    client = TestClient(create_demo_app())
    response = client.post("/execute_handler", json={"handler": "echo_payload", "payload": {"text": "hello"}})
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["data"]["request_id"] is not None
    assert body["result"]["data"]["trace_id"] is not None


def test_create_app_uses_environment_driven_runtime(monkeypatch):
    monkeypatch.setenv("LOGIC_FINGERPRINT_INSTANCE_ID", "api-node")
    monkeypatch.setenv("LOGIC_FINGERPRINT_DEFAULT_SOURCE", "gateway")
    monkeypatch.setenv("LOGIC_FINGERPRINT_BACKEND_TYPE", "memory")

    app = create_app()

    assert app.state.runtime.instance_id == "api-node"
    assert app.state.runtime.context_builder.default_source == "gateway"
    assert app.state.runtime_settings.backend_type == "memory"
    assert app.state.runtime.handler_registry.names() == []


def test_create_app_accepts_injected_runtime():
    runtime = build_demo_runtime(instance_id="injected-node")

    app = create_app(runtime=runtime)

    assert app.state.runtime is runtime
    assert app.state.runtime.instance_id == "injected-node"


def test_create_demo_app_registers_demo_handlers():
    app = create_demo_app()

    assert "sum_numbers" in app.state.runtime.handler_registry.names()
