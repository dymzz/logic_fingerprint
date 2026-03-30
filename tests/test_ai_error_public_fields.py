from __future__ import annotations

import pytest

from logicfp import create_protector
from logicfp.domain.models import HandlerRequest
from logicfp.user_mode import ErrorCode, ProtectRuntimeError


class FakeOpenAIRateLimitError(Exception):
    def __init__(self):
        super().__init__("TPM limit reached for this model")
        self.status_code = 429
        self.code = "rate_limit_exceeded"


FakeOpenAIRateLimitError.__module__ = "openai"


class FakeOpenAIAuthError(Exception):
    def __init__(self):
        super().__init__("Invalid API key")
        self.status_code = 401


FakeOpenAIAuthError.__module__ = "openai"


# ---------------------------------------------------------------------------
# simple=True — ProtectRuntimeError first-class fields
# ---------------------------------------------------------------------------


def test_simple_true_exposes_ai_error_code_on_exception():
    @create_protector().protect(simple=True)
    def guarded(request: HandlerRequest):
        raise FakeOpenAIRateLimitError()

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"x": 1})

    exc = exc_info.value
    assert exc.ai_error_code == "RATE_LIMIT_TOKEN"
    assert exc.retryable is True
    assert exc.provider == "openai"
    assert exc.severity == "warn"


def test_simple_true_exposes_auth_error_fields():
    @create_protector().protect(simple=True)
    def guarded(request: HandlerRequest):
        raise FakeOpenAIAuthError()

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"x": 1})

    exc = exc_info.value
    assert exc.ai_error_code == "AUTH_INVALID"
    assert exc.retryable is False
    assert exc.provider == "openai"
    assert exc.severity == "block"


def test_simple_true_fields_are_none_for_non_ai_error():
    @create_protector().protect(simple=True)
    def guarded(request: HandlerRequest):
        raise ValueError("plain error")

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"x": 1})

    exc = exc_info.value
    assert exc.ai_error_code is None
    assert exc.retryable is None
    assert exc.provider is None
    assert exc.severity is None


# ---------------------------------------------------------------------------
# simple=False — envelope top-level fields
# ---------------------------------------------------------------------------


def test_simple_false_envelope_exposes_ai_error_fields():
    @create_protector().protect(simple=False)
    def guarded(request: HandlerRequest):
        raise FakeOpenAIRateLimitError()

    result = guarded(payload={"x": 1})

    assert result["ok"] is False
    error = result["error"]
    assert error["ai_error_code"] == "RATE_LIMIT_TOKEN"
    assert error["retryable"] is True
    assert error["provider"] == "openai"
    assert error["severity"] == "warn"


def test_simple_false_envelope_fields_are_none_for_non_ai_error():
    @create_protector().protect(simple=False)
    def guarded(request: HandlerRequest):
        raise ValueError("plain error")

    result = guarded(payload={"x": 1})

    assert result["ok"] is False
    error = result["error"]
    assert error["ai_error_code"] is None
    assert error["retryable"] is None
    assert error["provider"] is None
    assert error["severity"] is None


def test_simple_false_envelope_retryable_false_for_auth():
    @create_protector().protect(simple=False)
    def guarded(request: HandlerRequest):
        raise FakeOpenAIAuthError()

    result = guarded(payload={"x": 1})

    error = result["error"]
    assert error["ai_error_code"] == "AUTH_INVALID"
    assert error["retryable"] is False
    assert error["severity"] == "block"


def test_simple_false_envelope_still_contains_details():
    @create_protector().protect(simple=False)
    def guarded(request: HandlerRequest):
        raise FakeOpenAIRateLimitError()

    result = guarded(payload={"x": 1})

    error = result["error"]
    assert "details" in error
    assert error["details"]["ai_error"]["code"] == "RATE_LIMIT_TOKEN"
