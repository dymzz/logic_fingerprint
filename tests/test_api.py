import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient
from logic_fingerprint.app_factory import create_app

def test_execute_handler_success_envelope():
    client = TestClient(create_app())
    response = client.post("/execute_handler", json={"handler": "sum_numbers", "payload": {"numbers": [1, 2, 3]}})
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["data"]["sum"] == 6

def test_execute_handler_validation_error_envelope():
    client = TestClient(create_app())
    response = client.post("/execute_handler", json={"handler": "sum_numbers", "payload": {"numbers": ["x"]}})
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "ERR_VALIDATION"
    assert "errors" in body["error"]["details"]

def test_execute_handler_autofills_context():
    client = TestClient(create_app())
    response = client.post("/execute_handler", json={"handler": "echo_payload", "payload": {"text": "hello"}})
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["data"]["request_id"] is not None
    assert body["result"]["data"]["trace_id"] is not None
