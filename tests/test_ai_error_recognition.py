import pytest

from logicfp import create_protector
from logicfp.domain.ai_error_recognizer import (
    build_ai_error_recognition,
    build_ai_error_classification_input,
    list_ai_error_recognizers,
    recognize_ai_error,
    register_ai_error_recognizer,
    unregister_ai_error_recognizer,
)
from logicfp.domain.models import HandlerRequest
from logicfp.user_mode import ErrorCode, ProtectRuntimeError


class FakeResponse:
    def __init__(
        self,
        *,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        request_id: str | None = None,
        error: dict[str, object] | None = None,
    ) -> None:
        self.status_code = status_code
        self.headers = headers or {}
        self.request_id = request_id
        self.error = error or {}


class FakeOpenAIRateLimitError(Exception):
    def __init__(self, message: str, *, status_code: int = 429, code: str = "rate_limit_exceeded") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


FakeOpenAIRateLimitError.__module__ = "openai"


class FakeOpenAINestedResponseRateLimitError(Exception):
    def __init__(self) -> None:
        super().__init__("Rate limit reached for gpt-5-mini")
        self.response = FakeResponse(
            status_code=429,
            headers={"retry-after": "7", "x-request-id": "req_nested_123"},
            request_id="req_nested_123",
            error={"code": "rate_limit_exceeded"},
        )
        self.body = {"model": "gpt-5-mini", "error": {"code": "rate_limit_exceeded"}}


FakeOpenAINestedResponseRateLimitError.__module__ = "openai"
FakeOpenAINestedResponseRateLimitError.__name__ = "RateLimitError"


class FakeOpenAIAuthError(Exception):
    def __init__(self, message: str = "Invalid API key", *, status_code: int = 401) -> None:
        super().__init__(message)
        self.status_code = status_code


FakeOpenAIAuthError.__module__ = "openai"


class FakeOpenAIQuotaError(Exception):
    def __init__(self) -> None:
        super().__init__("You exceeded your current quota, please check your plan and billing details.")
        self.status_code = 429
        self.code = "insufficient_quota"


FakeOpenAIQuotaError.__module__ = "openai"


class FakeOpenAIModelNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("The model `gpt-missing` was not found")
        self.status_code = 404
        self.code = "model_not_found"
        self.model = "gpt-missing"


FakeOpenAIModelNotFoundError.__module__ = "openai"


class FakeOpenAIInternalServerError(Exception):
    def __init__(self) -> None:
        super().__init__("OpenAI upstream internal server error")
        self.status_code = 500
        self.code = "internal_server_error"


FakeOpenAIInternalServerError.__module__ = "openai"


class FakeOpenAIConnectionError(ConnectionError):
    def __init__(self) -> None:
        super().__init__("Connection error while reaching OpenAI upstream")


FakeOpenAIConnectionError.__module__ = "openai"
FakeOpenAIConnectionError.__name__ = "APIConnectionError"


class FakeAnthropicRateLimitError(Exception):
    def __init__(self) -> None:
        super().__init__("Request rate limit exceeded for this workspace")
        self.status_code = 429
        self.code = "rate_limit_error"


FakeAnthropicRateLimitError.__module__ = "anthropic"
FakeAnthropicRateLimitError.__name__ = "RateLimitError"


class FakeAnthropicOverloadedError(Exception):
    def __init__(self) -> None:
        super().__init__("Anthropic API is temporarily overloaded")
        self.status_code = 529
        self.code = "overloaded_error"


FakeAnthropicOverloadedError.__module__ = "anthropic"
FakeAnthropicOverloadedError.__name__ = "InternalServerError"


class FakeOpenAIRefusalError(Exception):
    def __init__(self) -> None:
        super().__init__("The model refused this request due to safety policy.")
        self.refusal = "safety"
        self.finish_reason = "content_filter"


FakeOpenAIRefusalError.__module__ = "openai"


class FakeOpenAITruncatedError(Exception):
    def __init__(self) -> None:
        super().__init__("Response generation stopped because finish_reason=length")
        self.finish_reason = "length"


FakeOpenAITruncatedError.__module__ = "openai"


class FakeOpenAINestedChoicesTruncatedError(Exception):
    def __init__(self) -> None:
        super().__init__("OpenAI response stopped early")
        self.body = {
            "model": "gpt-5-mini",
            "choices": [
                {
                    "finish_reason": "length",
                }
            ],
        }


FakeOpenAINestedChoicesTruncatedError.__module__ = "openai"


class FakeAnthropicNestedRefusalError(Exception):
    def __init__(self) -> None:
        super().__init__("Anthropic response was blocked")
        self.body = {
            "model": "claude-3-5-sonnet",
            "stop_reason": "refusal",
            "refusal": "policy",
        }


FakeAnthropicNestedRefusalError.__module__ = "anthropic"


class FakeLangChainStreamError(Exception):
    def __init__(self) -> None:
        super().__init__("OpenAI stream interrupted before completion")
        self.stream_started = True
        self.received_chunks = 4
        self.finish_reason = None


FakeLangChainStreamError.__module__ = "langchain_openai"


class FakeLangChainOutputParserException(Exception):
    def __init__(self) -> None:
        super().__init__("Could not parse LLM output into the expected JSON shape")
        self.schema_name = "ReviewResult"


FakeLangChainOutputParserException.__module__ = "langchain_core.output_parsers"


class FakeLangChainToolArgsError(Exception):
    def __init__(self) -> None:
        super().__init__("tool input validation failed for search_docs")
        self.tool_name = "search_docs"


FakeLangChainToolArgsError.__module__ = "langchain_core.tools"


class FakeLangChainToolException(Exception):
    def __init__(self) -> None:
        super().__init__("tool execution failed while calling search_docs")
        self.tool_name = "search_docs"


FakeLangChainToolException.__module__ = "langchain_core.tools"
FakeLangChainToolException.__name__ = "ToolException"


class FakeToolTimeoutError(TimeoutError):
    def __init__(self) -> None:
        super().__init__("tool execution timed out")
        self.tool_name = "search_docs"


class FakeAnthropicAuthError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid API key provided")
        self.status_code = 401
        self.code = "authentication_error"


FakeAnthropicAuthError.__module__ = "anthropic"
FakeAnthropicAuthError.__name__ = "AuthenticationError"


class FakeAnthropicForbiddenError(Exception):
    def __init__(self) -> None:
        super().__init__("Permission denied for this resource")
        self.status_code = 403
        self.code = "permission_denied_error"


FakeAnthropicForbiddenError.__module__ = "anthropic"
FakeAnthropicForbiddenError.__name__ = "PermissionDeniedError"


class FakeAnthropicQuotaError(Exception):
    def __init__(self) -> None:
        super().__init__("Your credit balance is too low to access this model.")
        self.status_code = 429
        self.code = "insufficient_quota"


FakeAnthropicQuotaError.__module__ = "anthropic"


class FakeAnthropicModelNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("The model `claude-missing` was not found")
        self.status_code = 404
        self.code = "not_found_error"
        self.model = "claude-missing"


FakeAnthropicModelNotFoundError.__module__ = "anthropic"
FakeAnthropicModelNotFoundError.__name__ = "NotFoundError"


class FakeAnthropicContextTooLongError(Exception):
    def __init__(self) -> None:
        super().__init__("prompt is too long: 210000 tokens > 200000 maximum context length")
        self.status_code = 400
        self.code = "invalid_request_error"


FakeAnthropicContextTooLongError.__module__ = "anthropic"


class FakeAnthropicTokenRateLimitError(Exception):
    def __init__(self) -> None:
        super().__init__("Rate limit reached: token throughput limit exceeded")
        self.status_code = 429
        self.code = "rate_limit_error"


FakeAnthropicTokenRateLimitError.__module__ = "anthropic"
FakeAnthropicTokenRateLimitError.__name__ = "RateLimitError"


class FakeAnthropicUpstream5xxError(Exception):
    def __init__(self) -> None:
        super().__init__("Anthropic internal server error")
        self.status_code = 500


FakeAnthropicUpstream5xxError.__module__ = "anthropic"


class FakeLangChainToolNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("tool not found: summarize_docs")
        self.tool_name = "summarize_docs"


FakeLangChainToolNotFoundError.__module__ = "langchain_core.tools"


class FakePlainTimeoutError(TimeoutError):
    def __init__(self) -> None:
        super().__init__("read timed out")


class FakePlainConnectionError(ConnectionError):
    def __init__(self) -> None:
        super().__init__("connection refused to upstream host")


class FakeSchemaValidationError(Exception):
    def __init__(self) -> None:
        super().__init__("pydantic validation error: 2 validation errors for ReviewResult")
        self.schema_name = "ReviewResult"


class FakeEmptyResultError(Exception):
    def __init__(self) -> None:
        super().__init__("empty result returned from model")


def test_recognize_token_rate_limit() -> None:
    exc = FakeOpenAIRateLimitError("TPM limit reached for this model")

    recognition = recognize_ai_error(exc)

    assert recognition is not None
    assert recognition.code == "RATE_LIMIT_TOKEN"
    assert recognition.provider == "openai"
    assert recognition.retryable is True


def test_recognize_openai_rate_limit_from_nested_response_payload() -> None:
    recognition = recognize_ai_error(FakeOpenAINestedResponseRateLimitError())

    assert recognition is not None
    assert recognition.code == "RATE_LIMIT_REQUEST"
    assert recognition.provider == "openai"
    assert recognition.model == "gpt-5-mini"
    assert recognition.details["provider_request_id"] == "req_nested_123"
    assert recognition.details["retry_after_s"] == 7.0


def test_recognize_auth_invalid() -> None:
    recognition = recognize_ai_error(FakeOpenAIAuthError())

    assert recognition is not None
    assert recognition.code == "AUTH_INVALID"
    assert recognition.provider == "openai"
    assert recognition.retryable is False


def test_recognize_openai_quota_exhausted() -> None:
    recognition = recognize_ai_error(FakeOpenAIQuotaError())

    assert recognition is not None
    assert recognition.code == "QUOTA_EXHAUSTED"
    assert recognition.provider == "openai"
    assert recognition.retryable is False


def test_recognize_openai_model_not_found() -> None:
    recognition = recognize_ai_error(FakeOpenAIModelNotFoundError())

    assert recognition is not None
    assert recognition.code == "MODEL_NOT_FOUND"
    assert recognition.provider == "openai"
    assert recognition.model == "gpt-missing"


def test_recognize_openai_upstream_5xx() -> None:
    recognition = recognize_ai_error(FakeOpenAIInternalServerError())

    assert recognition is not None
    assert recognition.code == "UPSTREAM_5XX"
    assert recognition.provider == "openai"
    assert recognition.retryable is True


def test_recognize_openai_connection_error() -> None:
    recognition = recognize_ai_error(FakeOpenAIConnectionError())

    assert recognition is not None
    assert recognition.code == "NET_CONNECT"
    assert recognition.provider == "openai"
    assert recognition.retryable is True


def test_recognize_anthropic_rate_limit_request() -> None:
    recognition = recognize_ai_error(FakeAnthropicRateLimitError())

    assert recognition is not None
    assert recognition.code == "RATE_LIMIT_REQUEST"
    assert recognition.provider == "anthropic"
    assert recognition.retryable is True


def test_recognize_anthropic_upstream_overloaded() -> None:
    recognition = recognize_ai_error(FakeAnthropicOverloadedError())

    assert recognition is not None
    assert recognition.code == "UPSTREAM_OVERLOADED"
    assert recognition.provider == "anthropic"
    assert recognition.retryable is True


def test_recognize_safety_refusal() -> None:
    recognition = recognize_ai_error(FakeOpenAIRefusalError())

    assert recognition is not None
    assert recognition.code == "SAFETY_REFUSAL"
    assert recognition.provider == "openai"
    assert recognition.retryable is False


def test_recognize_output_truncated() -> None:
    recognition = recognize_ai_error(FakeOpenAITruncatedError())

    assert recognition is not None
    assert recognition.code == "OUTPUT_TRUNCATED"
    assert recognition.provider == "openai"
    assert recognition.details["finish_reason"] == "length"


def test_recognize_output_truncated_from_nested_choices() -> None:
    recognition = recognize_ai_error(FakeOpenAINestedChoicesTruncatedError())

    assert recognition is not None
    assert recognition.code == "OUTPUT_TRUNCATED"
    assert recognition.provider == "openai"
    assert recognition.model == "gpt-5-mini"
    assert recognition.details["finish_reason"] == "length"


def test_recognize_safety_refusal_from_nested_anthropic_body() -> None:
    recognition = recognize_ai_error(FakeAnthropicNestedRefusalError())

    assert recognition is not None
    assert recognition.code == "SAFETY_REFUSAL"
    assert recognition.provider == "anthropic"
    assert recognition.model == "claude-3-5-sonnet"
    assert recognition.details["stop_reason"] == "refusal"
    assert recognition.details["refusal"] == "policy"


def test_recognize_stream_broken() -> None:
    recognition = recognize_ai_error(FakeLangChainStreamError())

    assert recognition is not None
    assert recognition.code == "STREAM_BROKEN"
    assert recognition.provider == "langchain-openai"
    assert recognition.details["received_chunks"] == 4


def test_recognize_langchain_output_parse_error() -> None:
    recognition = recognize_ai_error(FakeLangChainOutputParserException())

    assert recognition is not None
    assert recognition.code == "OUTPUT_PARSE_ERROR"
    assert recognition.provider == "langchain"
    assert recognition.details["schema_name"] == "ReviewResult"


def test_recognize_langchain_tool_args_invalid() -> None:
    recognition = recognize_ai_error(FakeLangChainToolArgsError())

    assert recognition is not None
    assert recognition.code == "TOOL_ARGS_INVALID"
    assert recognition.provider == "langchain"
    assert recognition.details["tool_name"] == "search_docs"


def test_recognize_langchain_tool_exec_error() -> None:
    recognition = recognize_ai_error(FakeLangChainToolException())

    assert recognition is not None
    assert recognition.code == "TOOL_EXEC_ERROR"
    assert recognition.provider == "langchain"
    assert recognition.details["tool_name"] == "search_docs"


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


def test_model_classifier_input_reads_nested_response_fields() -> None:
    payload = build_ai_error_classification_input(FakeOpenAINestedResponseRateLimitError())

    assert payload["provider"] == "openai"
    assert payload["http_status"] == 429
    assert payload["provider_code"] == "rate_limit_exceeded"
    assert payload["provider_request_id"] == "req_nested_123"
    assert payload["retry_after_s"] == 7.0
    assert payload["model"] == "gpt-5-mini"


def test_model_classifier_input_reads_nested_finish_reason_from_choices() -> None:
    payload = build_ai_error_classification_input(FakeOpenAINestedChoicesTruncatedError())

    assert payload["provider"] == "openai"
    assert payload["model"] == "gpt-5-mini"
    assert payload["finish_reason"] == "length"


def test_custom_ai_error_recognizer_can_override_builtin_by_priority() -> None:
    def custom_recognizer(context):
        if context.class_name_lower == "fakeopenaiautherror":
            return build_ai_error_recognition(
                "MODEL_NOT_FOUND",
                provider=context.provider,
                model=context.model,
                matched_signals=("custom_test_recognizer",),
                details=context.base_details,
            )
        return None

    register_ai_error_recognizer("test-custom-priority", custom_recognizer, priority=10)
    try:
        recognition = recognize_ai_error(FakeOpenAIAuthError())
    finally:
        unregister_ai_error_recognizer("test-custom-priority")

    assert recognition is not None
    assert recognition.code == "MODEL_NOT_FOUND"
    assert recognition.provider == "openai"


def test_local_ai_error_recognizer_precedes_registered_chain() -> None:
    def local_recognizer(context):
        if context.class_name_lower == "fakeopenaiautherror":
            return build_ai_error_recognition(
                "AUTH_FORBIDDEN",
                provider=context.provider,
                model=context.model,
                matched_signals=("local_test_recognizer",),
                details=context.base_details,
            )
        return None

    recognition = recognize_ai_error(
        FakeOpenAIAuthError(),
        recognizers=(local_recognizer,),
    )

    assert recognition is not None
    assert recognition.code == "AUTH_FORBIDDEN"
    assert recognition.provider == "openai"


def test_list_ai_error_recognizers_includes_registered_custom_entry() -> None:
    def passthrough_recognizer(context):
        return None

    register_ai_error_recognizer("test-list-entry", passthrough_recognizer, priority=130)
    try:
        names = [item.name for item in list_ai_error_recognizers()]
    finally:
        unregister_ai_error_recognizer("test-list-entry")

    assert "openai" in names
    assert "anthropic" in names
    assert "langchain" in names
    assert "test-list-entry" in names


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


# ---------------------------------------------------------------------------
# Anthropic provider – missing coverage
# ---------------------------------------------------------------------------


def test_recognize_anthropic_auth_invalid() -> None:
    recognition = recognize_ai_error(FakeAnthropicAuthError())

    assert recognition is not None
    assert recognition.code == "AUTH_INVALID"
    assert recognition.provider == "anthropic"
    assert recognition.retryable is False


def test_recognize_anthropic_auth_forbidden() -> None:
    recognition = recognize_ai_error(FakeAnthropicForbiddenError())

    assert recognition is not None
    assert recognition.code == "AUTH_FORBIDDEN"
    assert recognition.provider == "anthropic"
    assert recognition.retryable is False


def test_recognize_anthropic_quota_exhausted() -> None:
    recognition = recognize_ai_error(FakeAnthropicQuotaError())

    assert recognition is not None
    assert recognition.code == "QUOTA_EXHAUSTED"
    assert recognition.provider == "anthropic"
    assert recognition.retryable is False


def test_recognize_anthropic_model_not_found() -> None:
    recognition = recognize_ai_error(FakeAnthropicModelNotFoundError())

    assert recognition is not None
    assert recognition.code == "MODEL_NOT_FOUND"
    assert recognition.provider == "anthropic"
    assert recognition.model == "claude-missing"


def test_recognize_anthropic_context_too_long() -> None:
    recognition = recognize_ai_error(FakeAnthropicContextTooLongError())

    assert recognition is not None
    assert recognition.code == "CONTEXT_TOO_LONG"
    assert recognition.provider == "anthropic"
    assert recognition.retryable is False


def test_recognize_anthropic_token_rate_limit() -> None:
    recognition = recognize_ai_error(FakeAnthropicTokenRateLimitError())

    assert recognition is not None
    assert recognition.code == "RATE_LIMIT_TOKEN"
    assert recognition.provider == "anthropic"
    assert recognition.retryable is True


def test_recognize_anthropic_upstream_5xx() -> None:
    recognition = recognize_ai_error(FakeAnthropicUpstream5xxError())

    assert recognition is not None
    assert recognition.code == "UPSTREAM_5XX"
    assert recognition.provider == "anthropic"
    assert recognition.retryable is True


# ---------------------------------------------------------------------------
# LangChain provider – missing coverage
# ---------------------------------------------------------------------------


def test_recognize_langchain_tool_not_found() -> None:
    recognition = recognize_ai_error(FakeLangChainToolNotFoundError())

    assert recognition is not None
    assert recognition.code == "TOOL_NOT_FOUND"
    assert recognition.provider == "langchain"
    assert recognition.details["tool_name"] == "summarize_docs"


# ---------------------------------------------------------------------------
# Generic transport – missing coverage
# ---------------------------------------------------------------------------


def test_recognize_plain_timeout_as_net_timeout() -> None:
    recognition = recognize_ai_error(FakePlainTimeoutError())

    assert recognition is not None
    assert recognition.code == "NET_TIMEOUT"
    assert recognition.retryable is True
    assert recognition.provider is None


def test_recognize_plain_connection_error_as_net_connect() -> None:
    recognition = recognize_ai_error(FakePlainConnectionError())

    assert recognition is not None
    assert recognition.code == "NET_CONNECT"
    assert recognition.retryable is True
    assert recognition.provider is None


# ---------------------------------------------------------------------------
# Generic output – missing coverage
# ---------------------------------------------------------------------------


def test_recognize_schema_validation_error() -> None:
    recognition = recognize_ai_error(FakeSchemaValidationError())

    assert recognition is not None
    assert recognition.code == "OUTPUT_SCHEMA_INVALID"
    assert recognition.retryable is False
    assert recognition.details["schema_name"] == "ReviewResult"


def test_recognize_empty_result_error() -> None:
    recognition = recognize_ai_error(FakeEmptyResultError())

    assert recognition is not None
    assert recognition.code == "EMPTY_RESULT"
    assert recognition.retryable is False

