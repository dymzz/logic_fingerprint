import pytest

from logicfp import create_protector
from logicfp.domain.ai_error_recognizer import (
    build_ai_error_classification_input,
    recognize_ai_error,
)
from logicfp.domain.models import HandlerRequest
from logicfp.user_mode import ErrorCode, ProtectRuntimeError


class FakeOpenAIRateLimitError(Exception):
    def __init__(self, message: str, *, status_code: int = 429, code: str = "rate_limit_exceeded") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


FakeOpenAIRateLimitError.__module__ = "openai"


class FakeOpenAIAuthError(Exception):
    def __init__(self, message: str = "Invalid API key", *, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


FakeOpenAIAuthError.__module__ = "openai"


class FakeLangChainStreamError(Exception):
    def __init__(self) -> None:
        super().__init__("OpenAI stream interrupted before completion")
        self.stream_started = True
        self.received_chunks = 4
        self.finish_reason = None


FakeLangChainStreamError.__module__ = "langchain_openai"


class FakeToolTimeoutError(TimeoutError):
    def __init__(self) -> None:
        super().__init__("tool execution timed out")
        self.tool_name = "search_docs"


def test_recognize_token_rate_limit() -> None:
    exc = FakeOpenAIRateLimitError("TPM limit reached for this model")

    recognition = recognize_ai_error(exc)

    assert recognition is not None
    assert recognition.code == "RATE_LIMIT_TOKEN"
    assert recognition.provider == "openai"
    assert recognition.retryable is True


def test_recognize_auth_invalid() -> None:
    recognition = recognize_ai_error(FakeOpenAIAuthError())

    assert recognition is not None
    assert recognition.code == "AUTH_INVALID"
    assert recognition.provider == "openai"
    assert recognition.retryable is False


def test_recognize_stream_broken() -> None:
    recognition = recognize_ai_error(FakeLangChainStreamError())

    assert recognition is not None
    assert recognition.code == "STREAM_BROKEN"
    assert recognition.provider == "langchain-openai"
    assert recognition.details["received_chunks"] == 4


def test_recognize_tool_timeout() -> None:
    recognition = recognize_ai_error(FakeToolTimeoutError())

    assert recognition is not None
    assert recognition.code == "TOOL_TIMEOUT"
    assert recognition.details["tool_name"] == "search_docs"


def test_protect_runtime_error_includes_ai_error_details() -> None:
    @create_protector().protect(simple=True)
    def guarded(request: HandlerRequest):
        raise FakeOpenAIRateLimitError("TPM limit reached for this model")

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"value": 1})

    assert exc_info.value.code == ErrorCode.ERR_UNKNOWN.value
    assert exc_info.value.details["ai_error"]["code"] == "RATE_LIMIT_TOKEN"
    assert exc_info.value.details["ai_error"]["retryable"] is True


def test_model_classifier_can_recognize_unknown_error() -> None:
    class FakeModelError(Exception):
        pass

    def classifier(payload):
        assert payload["exception_type"] == "FakeModelError"
        return {
            "code": "UPSTREAM_OVERLOADED",
            "provider": "openai",
            "matched_signals": ["model_classifier", "provider_semantics"],
            "details": {"reason": "classified by model"},
        }

    recognition = recognize_ai_error(FakeModelError("provider semantic mismatch"), model_classifier=classifier)

    assert recognition is not None
    assert recognition.code == "UPSTREAM_OVERLOADED"
    assert recognition.provider == "openai"
    assert recognition.matched_signals == ("model_classifier", "provider_semantics")
    assert recognition.details["reason"] == "classified by model"


def test_model_classifier_input_contains_useful_fields() -> None:
    exc = FakeOpenAIRateLimitError("TPM limit reached for this model")

    payload = build_ai_error_classification_input(exc)

    assert payload["exception_type"] == "FakeOpenAIRateLimitError"
    assert payload["provider"] == "openai"
    assert payload["http_status"] == 429
    assert payload["provider_code"] == "rate_limit_exceeded"


def test_create_protector_allows_optional_model_classifier_for_ai_error_details() -> None:
    class FakeProviderError(Exception):
        pass

    def classifier(payload):
        return {
            "code": "AUTH_INVALID",
            "provider": "openai",
            "details": {"source": "api-model"},
        }

    protector = create_protector(advanced={"ai_error_classifier": classifier})

    @protector.protect(simple=True)
    def guarded(request: HandlerRequest):
        raise FakeProviderError("credential rejected upstream")

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"value": 1})

    assert exc_info.value.details["ai_error"]["code"] == "AUTH_INVALID"
    assert exc_info.value.details["ai_error"]["details"]["source"] == "api-model"


def test_error_fact_and_policy_are_added_for_validation_failure() -> None:
    from pydantic import BaseModel

    class InputModel(BaseModel):
        quantity: int

    @create_protector().protect(input_model=InputModel, simple=False)
    def guarded(request: HandlerRequest):
        return {"value": request.payload["quantity"]}

    result = guarded(payload={"quantity": "bad"})

    fact = result["error"]["details"]["error_fact"]
    policy = result["error"]["details"]["error_policy"]

    assert fact["stage"] == "input"
    assert fact["source"] == "caller"
    assert fact["recoverability"] == "non_recoverable"
    assert fact["details"]["certainty"] == "deterministic"
    assert fact["details"]["impact"] == "fatal"
    assert policy["action"] == "block"
    assert policy["details"]["user_effect"] == "hard_error"


def test_error_fact_and_policy_are_added_for_dependency_failure() -> None:
    @create_protector().protect(simple=False)
    def guarded(request: HandlerRequest):
        raise FakeOpenAIRateLimitError("TPM limit reached for this model")

    result = guarded(payload={"value": 1})

    fact = result["error"]["details"]["error_fact"]
    policy = result["error"]["details"]["error_policy"]

    assert fact["stage"] == "dependency"
    assert fact["source"] == "dependency"
    assert fact["recoverability"] == "retryable"
    assert fact["details"]["impact"] == "major"
    assert policy["action"] == "retry"
    assert policy["details"]["user_effect"] == "soft_notice"


def test_optional_action_resolver_can_override_unknown_policy() -> None:
    class FakeUnknownError(Exception):
        pass

    def action_resolver(payload):
        assert set(payload) == {"fact", "default_action", "default_policy"}
        assert payload["fact"]["details"]["certainty"] == "deterministic"
        assert payload["fact"]["source"] == "unknown"
        assert payload["default_action"]["action"] == "warn"
        assert payload["default_policy"]["action"] == "warn"
        return {
            "action": "fallback",
            "user_effect": "soft_notice",
            "observability": "shadow_only",
        }

    protector = create_protector(advanced={"error_action_resolver": action_resolver})

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        raise FakeUnknownError("unexpected branch")

    result = guarded(payload={"value": 1})

    assert result["error"]["details"]["error_policy"]["action"] == "fallback"
    assert result["error"]["details"]["error_policy"]["details"]["observability"] == "shadow_only"


def test_action_resolver_can_return_minimal_action_only() -> None:
    class FakeUnknownError(Exception):
        pass

    def action_resolver(payload):
        return {"action": "fallback"}

    protector = create_protector(advanced={"error_action_resolver": action_resolver})

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        raise FakeUnknownError("unexpected branch")

    result = guarded(payload={"value": 1})

    assert result["error"]["details"]["error_policy"]["action"] == "fallback"
    assert result["error"]["details"]["error_policy"]["details"]["user_effect"] == "soft_notice"
    assert result["error"]["details"]["error_policy"]["details"]["observability"] == "aggregate"


def test_legacy_error_policy_resolver_still_works_with_warning() -> None:
    class FakeUnknownError(Exception):
        pass

    def legacy_policy_resolver(payload):
        return {"action": "fallback"}

    with pytest.warns(DeprecationWarning, match="error_policy_resolver"):
        protector = create_protector(advanced={"error_policy_resolver": legacy_policy_resolver})

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        raise FakeUnknownError("unexpected branch")

    result = guarded(payload={"value": 1})

    assert result["error"]["details"]["error_policy"]["action"] == "fallback"

