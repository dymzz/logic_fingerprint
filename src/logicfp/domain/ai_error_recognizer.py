from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .ai_error_catalog import get_ai_error_descriptor

AIErrorClassifier = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class AIErrorRecognition:
    code: str
    category: str
    retryable: bool | None
    severity: str
    phase: str
    provider: str | None = None
    model: str | None = None
    matched_signals: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "retryable": self.retryable,
            "severity": self.severity,
            "phase": self.phase,
            "provider": self.provider,
            "model": self.model,
            "matched_signals": list(self.matched_signals),
            "details": dict(self.details),
        }


def build_ai_error_recognition(
    code: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    matched_signals: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> AIErrorRecognition | None:
    descriptor = get_ai_error_descriptor(code)
    if descriptor is None:
        return None
    return AIErrorRecognition(
        code=descriptor.code,
        category=descriptor.category.value,
        retryable=descriptor.retryable,
        severity=descriptor.severity.value,
        phase=descriptor.phase.value,
        provider=provider,
        model=model,
        matched_signals=matched_signals,
        details=details or {},
    )


def recognize_ai_error(
    exc: Exception,
    *,
    model_classifier: AIErrorClassifier | None = None,
) -> AIErrorRecognition | None:
    recognition = _recognize_ai_error_rules(exc)
    if recognition is not None:
        return recognition
    if model_classifier is None:
        return None
    return _recognize_ai_error_by_model(exc, model_classifier)


def _recognize_ai_error_rules(exc: Exception) -> AIErrorRecognition | None:
    message = _exception_message(exc)
    message_lower = message.lower()
    module_lower = exc.__class__.__module__.lower()
    class_name_lower = exc.__class__.__name__.lower()
    provider = _detect_provider(module_lower, message_lower)
    model = _read_first_attr(exc, "model", "model_name", "model_id")
    status_code = _read_status_code(exc)
    provider_code = _read_provider_code(exc)
    retry_after_s = _read_retry_after(exc)
    base_details = _compact_details(
        http_status=status_code,
        provider_code=provider_code,
        provider_type=module_lower or None,
        provider_request_id=_read_first_attr(exc, "request_id", "provider_request_id"),
        retry_after_s=retry_after_s,
        finish_reason=_read_first_attr(exc, "finish_reason"),
        stream_started=_read_first_attr(exc, "stream_started"),
        received_chunks=_read_first_attr(exc, "received_chunks"),
        input_tokens=_read_first_attr(exc, "input_tokens", "prompt_tokens"),
        output_tokens=_read_first_attr(exc, "output_tokens", "completion_tokens"),
        max_output_tokens=_read_first_attr(exc, "max_output_tokens", "max_tokens"),
        tool_name=_read_first_attr(exc, "tool_name"),
        tool_call_id=_read_first_attr(exc, "tool_call_id"),
        schema_name=_read_first_attr(exc, "schema_name"),
        raw_error_type=exc.__class__.__name__,
        raw_error_message=message,
    )

    if _is_tool_timeout(message_lower, class_name_lower, exc):
        return build_ai_error_recognition(
            "TOOL_TIMEOUT",
            provider=provider,
            model=model,
            matched_signals=("tool_timeout",),
            details=base_details,
        )

    if _is_timeout(message_lower, class_name_lower, exc):
        return build_ai_error_recognition(
            "NET_TIMEOUT",
            provider=provider,
            model=model,
            matched_signals=("timeout",),
            details=base_details,
        )

    if _is_token_rate_limit(status_code, provider_code, message_lower):
        return build_ai_error_recognition(
            "RATE_LIMIT_TOKEN",
            provider=provider,
            model=model,
            matched_signals=("http_429", "token_rate_limit"),
            details=base_details,
        )

    if _is_request_rate_limit(status_code, provider_code, message_lower):
        return build_ai_error_recognition(
            "RATE_LIMIT_REQUEST",
            provider=provider,
            model=model,
            matched_signals=("http_429", "request_rate_limit"),
            details=base_details,
        )

    if _is_auth_invalid(status_code, provider_code, message_lower):
        return build_ai_error_recognition(
            "AUTH_INVALID",
            provider=provider,
            model=model,
            matched_signals=("auth_invalid",),
            details=base_details,
        )

    if _is_auth_forbidden(status_code, provider_code, message_lower):
        return build_ai_error_recognition(
            "AUTH_FORBIDDEN",
            provider=provider,
            model=model,
            matched_signals=("auth_forbidden",),
            details=base_details,
        )

    if _is_upstream_overloaded(status_code, provider_code, message_lower):
        return build_ai_error_recognition(
            "UPSTREAM_OVERLOADED",
            provider=provider,
            model=model,
            matched_signals=("upstream_overloaded",),
            details=base_details,
        )

    if _is_stream_broken(message_lower, class_name_lower, exc):
        return build_ai_error_recognition(
            "STREAM_BROKEN",
            provider=provider,
            model=model,
            matched_signals=("stream_broken",),
            details=base_details,
        )

    if _is_context_too_long(status_code, provider_code, message_lower):
        return build_ai_error_recognition(
            "CONTEXT_TOO_LONG",
            provider=provider,
            model=model,
            matched_signals=("context_too_long",),
            details=base_details,
        )

    return None


def _recognize_ai_error_by_model(
    exc: Exception,
    model_classifier: AIErrorClassifier,
) -> AIErrorRecognition | None:
    payload = build_ai_error_classification_input(exc)
    try:
        result = model_classifier(payload)
    except Exception:
        return None
    return _normalize_model_classifier_result(result, payload)


def build_ai_error_classification_input(exc: Exception) -> dict[str, Any]:
    message = _exception_message(exc)
    module_lower = exc.__class__.__module__.lower()
    provider = _detect_provider(module_lower, message.lower())
    return _compact_details(
        exception_type=exc.__class__.__name__,
        exception_module=exc.__class__.__module__,
        message=message,
        provider=provider,
        model=_read_first_attr(exc, "model", "model_name", "model_id"),
        http_status=_read_status_code(exc),
        provider_code=_read_provider_code(exc),
        provider_request_id=_read_first_attr(exc, "request_id", "provider_request_id"),
        retry_after_s=_read_retry_after(exc),
        finish_reason=_read_first_attr(exc, "finish_reason"),
        stream_started=_read_first_attr(exc, "stream_started"),
        received_chunks=_read_first_attr(exc, "received_chunks"),
        input_tokens=_read_first_attr(exc, "input_tokens", "prompt_tokens"),
        output_tokens=_read_first_attr(exc, "output_tokens", "completion_tokens"),
        max_output_tokens=_read_first_attr(exc, "max_output_tokens", "max_tokens"),
        tool_name=_read_first_attr(exc, "tool_name"),
        tool_call_id=_read_first_attr(exc, "tool_call_id"),
        schema_name=_read_first_attr(exc, "schema_name"),
    )


def _normalize_model_classifier_result(
    result: dict[str, Any] | AIErrorRecognition | None,
    payload: dict[str, Any],
) -> AIErrorRecognition | None:
    if result is None:
        return None
    if isinstance(result, AIErrorRecognition):
        return result
    if not isinstance(result, dict):
        return None

    code = result.get("code")
    if not isinstance(code, str) or not code:
        return None

    details = result.get("details")
    if not isinstance(details, dict):
        details = {}
    merged_details = dict(payload)
    merged_details.update(details)

    matched_signals = result.get("matched_signals")
    if isinstance(matched_signals, list):
        matched_signals = tuple(str(item) for item in matched_signals)
    elif isinstance(matched_signals, tuple):
        matched_signals = tuple(str(item) for item in matched_signals)
    else:
        matched_signals = ("model_classifier",)

    return build_ai_error_recognition(
        code,
        provider=_coerce_optional_str(result.get("provider")) or _coerce_optional_str(payload.get("provider")),
        model=_coerce_optional_str(result.get("model")) or _coerce_optional_str(payload.get("model")),
        matched_signals=matched_signals,
        details=merged_details,
    )


def _exception_message(exc: Exception) -> str:
    message = getattr(exc, "message", None)
    if isinstance(message, str) and message:
        return message
    return str(exc)


def _detect_provider(module_lower: str, message_lower: str) -> str | None:
    if "langchain" in module_lower:
        if "openai" in message_lower:
            return "langchain-openai"
        return "langchain"
    if "openai" in module_lower or "openai" in message_lower:
        return "openai"
    if "anthropic" in module_lower or "anthropic" in message_lower:
        return "anthropic"
    return None


def _read_first_attr(obj: Any, *names: str) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _read_status_code(exc: Exception) -> int | None:
    for attr_name in ("status_code", "http_status", "status"):
        value = getattr(exc, attr_name, None)
        if isinstance(value, int):
            return value

    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int):
            return value

    return None


def _read_provider_code(exc: Exception) -> str | None:
    for attr_name in ("code", "error_code", "provider_code"):
        value = getattr(exc, attr_name, None)
        if isinstance(value, str) and value:
            return value
    return None


def _read_retry_after(exc: Exception) -> float | int | None:
    for attr_name in ("retry_after", "retry_after_s"):
        value = getattr(exc, attr_name, None)
        if isinstance(value, (int, float)):
            return value

    response = getattr(exc, "response", None)
    if response is not None:
        headers = getattr(response, "headers", None)
        if hasattr(headers, "get"):
            retry_after = headers.get("retry-after")
            if retry_after is not None:
                try:
                    return float(retry_after)
                except (TypeError, ValueError):
                    return None
    return None


def _compact_details(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def _is_timeout(message_lower: str, class_name_lower: str, exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    timeout_tokens = ("timeout", "timed out", "read timed out", "connect timed out")
    return "timeout" in class_name_lower or any(token in message_lower for token in timeout_tokens)


def _is_tool_timeout(message_lower: str, class_name_lower: str, exc: Exception) -> bool:
    tool_name = _read_first_attr(exc, "tool_name")
    if tool_name and _is_timeout(message_lower, class_name_lower, exc):
        return True
    return "tool" in message_lower and _is_timeout(message_lower, class_name_lower, exc)


def _is_token_rate_limit(status_code: int | None, provider_code: str | None, message_lower: str) -> bool:
    if status_code != 429:
        return False
    provider_code_lower = (provider_code or "").lower()
    return any(
        token in message_lower or token in provider_code_lower
        for token in ("token", "tpm", "throughput", "tokens per min")
    )


def _is_request_rate_limit(status_code: int | None, provider_code: str | None, message_lower: str) -> bool:
    if status_code != 429:
        return False
    if _is_token_rate_limit(status_code, provider_code, message_lower):
        return False
    provider_code_lower = (provider_code or "").lower()
    return any(
        token in message_lower or token in provider_code_lower
        for token in ("rate limit", "rpm", "rps", "too many requests", "request limit")
    )


def _is_auth_invalid(status_code: int | None, provider_code: str | None, message_lower: str) -> bool:
    provider_code_lower = (provider_code or "").lower()
    if status_code == 401:
        return True
    return any(
        token in message_lower or token in provider_code_lower
        for token in ("invalid api key", "incorrect api key", "missing api key", "unauthorized")
    )


def _is_auth_forbidden(status_code: int | None, provider_code: str | None, message_lower: str) -> bool:
    provider_code_lower = (provider_code or "").lower()
    if status_code == 403:
        return True
    return any(
        token in message_lower or token in provider_code_lower
        for token in ("permission denied", "forbidden", "not allowed to use this model")
    )


def _is_upstream_overloaded(status_code: int | None, provider_code: str | None, message_lower: str) -> bool:
    provider_code_lower = (provider_code or "").lower()
    if status_code in {503, 529}:
        return True
    return any(
        token in message_lower or token in provider_code_lower
        for token in ("overloaded", "temporarily unavailable", "server overloaded")
    )


def _is_stream_broken(message_lower: str, class_name_lower: str, exc: Exception) -> bool:
    stream_started = _read_first_attr(exc, "stream_started")
    if stream_started:
        finish_reason = _read_first_attr(exc, "finish_reason")
        if finish_reason in (None, ""):
            return True
    if "stream" not in message_lower and "stream" not in class_name_lower:
        return False
    return any(
        token in message_lower
        for token in ("broken", "closed", "incomplete", "interrupted", "connection reset")
    )


def _is_context_too_long(status_code: int | None, provider_code: str | None, message_lower: str) -> bool:
    provider_code_lower = (provider_code or "").lower()
    if status_code == 400 and "context" in message_lower and "length" in message_lower:
        return True
    return any(
        token in message_lower or token in provider_code_lower
        for token in ("context length exceeded", "maximum context length", "too many tokens")
    )


