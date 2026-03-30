from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .ai_error_catalog import get_ai_error_descriptor
from .providers._context import (
    RecognitionContext,
    build_recognition_context,
    coerce_optional_str,
    compact_details,
    detect_provider,
    exception_message,
    read_first_attr,
    read_nested_value,
)

AIErrorClassifier = Callable[[dict[str, Any]], Any]
AIErrorRecognizer = Callable[[RecognitionContext], "AIErrorRecognition | None"]


@dataclass(frozen=True)
class RegisteredAIErrorRecognizer:
    name: str
    priority: int
    recognizer: AIErrorRecognizer


_REGISTERED_AI_ERROR_RECOGNIZERS: list[RegisteredAIErrorRecognizer] = []


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
    recognizers: Iterable[AIErrorRecognizer] | None = None,
) -> AIErrorRecognition | None:
    recognition = _recognize_ai_error_rules(exc, recognizers=recognizers)
    if recognition is not None:
        return recognition
    if model_classifier is None:
        return None
    return _recognize_ai_error_by_model(exc, model_classifier)


def register_ai_error_recognizer(
    name: str,
    recognizer: AIErrorRecognizer,
    *,
    priority: int = 100,
) -> None:
    normalized_name = name.strip()
    if not normalized_name:
        raise ValueError("Recognizer name must not be empty.")
    unregister_ai_error_recognizer(normalized_name)
    _REGISTERED_AI_ERROR_RECOGNIZERS.append(
        RegisteredAIErrorRecognizer(
            name=normalized_name,
            priority=priority,
            recognizer=recognizer,
        )
    )
    _REGISTERED_AI_ERROR_RECOGNIZERS.sort(key=lambda item: (item.priority, item.name))


def unregister_ai_error_recognizer(name: str) -> None:
    normalized_name = name.strip()
    _REGISTERED_AI_ERROR_RECOGNIZERS[:] = [
        item for item in _REGISTERED_AI_ERROR_RECOGNIZERS if item.name != normalized_name
    ]


def list_ai_error_recognizers() -> tuple[RegisteredAIErrorRecognizer, ...]:
    combined = [*_builtin_ai_error_recognizers(), *_REGISTERED_AI_ERROR_RECOGNIZERS]
    combined.sort(key=lambda item: (item.priority, item.name))
    return tuple(combined)


def _recognize_ai_error_rules(
    exc: Exception,
    *,
    recognizers: Iterable[AIErrorRecognizer] | None = None,
) -> AIErrorRecognition | None:
    context = build_recognition_context(exc)

    for recognizer in tuple(recognizers or ()):
        recognition = recognizer(context)
        if recognition is not None:
            return recognition

    if _is_tool_timeout(context):
        return build_ai_error_recognition(
            "TOOL_TIMEOUT",
            provider=context.provider,
            model=context.model,
            matched_signals=("tool_timeout",),
            details=context.base_details,
        )

    if _is_timeout(context):
        return build_ai_error_recognition(
            "NET_TIMEOUT",
            provider=context.provider,
            model=context.model,
            matched_signals=("timeout",),
            details=context.base_details,
        )

    if _is_safety_refusal(context):
        return build_ai_error_recognition(
            "SAFETY_REFUSAL",
            provider=context.provider,
            model=context.model,
            matched_signals=("safety_refusal",),
            details=context.base_details,
        )

    if _is_output_truncated(context):
        return build_ai_error_recognition(
            "OUTPUT_TRUNCATED",
            provider=context.provider,
            model=context.model,
            matched_signals=("output_truncated",),
            details=context.base_details,
        )

    if _is_stream_broken(context):
        return build_ai_error_recognition(
            "STREAM_BROKEN",
            provider=context.provider,
            model=context.model,
            matched_signals=("stream_broken",),
            details=context.base_details,
        )

    if _is_connect_error(context):
        return build_ai_error_recognition(
            "NET_CONNECT",
            provider=context.provider,
            model=context.model,
            matched_signals=("connect_error",),
            details=context.base_details,
        )

    for recognizer in _iter_registered_ai_error_recognizers():
        recognition = recognizer(context)
        if recognition is not None:
            return recognition

    if _is_upstream_overloaded(context):
        return build_ai_error_recognition(
            "UPSTREAM_OVERLOADED",
            provider=context.provider,
            model=context.model,
            matched_signals=("upstream_overloaded",),
            details=context.base_details,
        )

    return None


def _builtin_ai_error_recognizers() -> tuple[RegisteredAIErrorRecognizer, ...]:
    from .providers.anthropic_recognizer import recognize_anthropic_error
    from .providers.langchain_recognizer import recognize_langchain_error
    from .providers.openai_recognizer import recognize_openai_error

    return (
        RegisteredAIErrorRecognizer(
            name="openai",
            priority=100,
            recognizer=recognize_openai_error,
        ),
        RegisteredAIErrorRecognizer(
            name="anthropic",
            priority=110,
            recognizer=recognize_anthropic_error,
        ),
        RegisteredAIErrorRecognizer(
            name="langchain",
            priority=120,
            recognizer=recognize_langchain_error,
        ),
    )


def _iter_registered_ai_error_recognizers() -> tuple[AIErrorRecognizer, ...]:
    return tuple(item.recognizer for item in list_ai_error_recognizers())


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
    context = build_recognition_context(exc)
    return compact_details(
        exception_type=exc.__class__.__name__,
        exception_module=exc.__class__.__module__,
        message=context.message,
        provider=detect_provider(context.module_lower, context.message_lower),
        model=context.model,
        http_status=context.status_code,
        provider_code=context.provider_code,
        provider_request_id=read_nested_value(exc, "request_id", "provider_request_id", "request-id", "x-request-id"),
        retry_after_s=context.retry_after_s,
        finish_reason=read_nested_value(exc, "finish_reason"),
        stop_reason=read_nested_value(exc, "stop_reason"),
        refusal=read_nested_value(exc, "refusal"),
        stream_started=read_nested_value(exc, "stream_started"),
        received_chunks=read_nested_value(exc, "received_chunks"),
        input_tokens=read_nested_value(exc, "input_tokens", "prompt_tokens"),
        output_tokens=read_nested_value(exc, "output_tokens", "completion_tokens"),
        max_output_tokens=read_nested_value(exc, "max_output_tokens", "max_tokens"),
        tool_name=read_nested_value(exc, "tool_name"),
        tool_call_id=read_nested_value(exc, "tool_call_id"),
        schema_name=read_nested_value(exc, "schema_name"),
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
        provider=coerce_optional_str(result.get("provider")) or coerce_optional_str(payload.get("provider")),
        model=coerce_optional_str(result.get("model")) or coerce_optional_str(payload.get("model")),
        matched_signals=matched_signals,
        details=merged_details,
    )


def _is_timeout(context: RecognitionContext) -> bool:
    if isinstance(context.exc, TimeoutError):
        return True
    timeout_tokens = ("timeout", "timed out", "read timed out", "connect timed out")
    return "timeout" in context.class_name_lower or any(token in context.message_lower for token in timeout_tokens)


def _is_tool_timeout(context: RecognitionContext) -> bool:
    tool_name = read_nested_value(context.exc, "tool_name")
    if tool_name and _is_timeout(context):
        return True
    return "tool" in context.message_lower and _is_timeout(context)


def _is_upstream_overloaded(context: RecognitionContext) -> bool:
    provider_code_lower = (context.provider_code or "").lower()
    if context.status_code in {503, 529}:
        return True
    return any(
        token in context.message_lower or token in provider_code_lower
        for token in ("overloaded", "temporarily unavailable", "server overloaded")
    )


def _is_safety_refusal(context: RecognitionContext) -> bool:
    refusal = read_nested_value(context.exc, "refusal")
    stop_reason = read_nested_value(context.exc, "stop_reason")
    finish_reason = read_nested_value(context.exc, "finish_reason")
    if isinstance(refusal, str) and refusal.strip():
        return True
    if isinstance(refusal, bool) and refusal:
        return True
    refusal_tokens = (
        "refusal",
        "refused",
        "content filter",
        "safety",
        "policy",
        "blocked content",
    )
    if isinstance(stop_reason, str) and stop_reason.lower() in {"refusal", "safety", "content_filter"}:
        return True
    if isinstance(finish_reason, str) and finish_reason.lower() in {"content_filter", "safety"}:
        return True
    return any(token in context.message_lower for token in refusal_tokens)


def _is_output_truncated(context: RecognitionContext) -> bool:
    finish_reason = read_nested_value(context.exc, "finish_reason")
    stop_reason = read_nested_value(context.exc, "stop_reason")
    if isinstance(finish_reason, str) and finish_reason.lower() in {"length", "max_tokens"}:
        return True
    if isinstance(stop_reason, str) and stop_reason.lower() in {"max_tokens", "length"}:
        return True
    return any(
        token in context.message_lower
        for token in (
            "finish_reason=length",
            "output truncated",
            "truncated output",
            "maximum output tokens",
        )
    )


def _is_connect_error(context: RecognitionContext) -> bool:
    if read_nested_value(context.exc, "stream_started"):
        return False
    if isinstance(context.exc, ConnectionError):
        return True
    connect_tokens = (
        "connection error",
        "connection reset",
        "connection refused",
        "dns",
        "name resolution",
        "tls",
        "ssl",
        "socket",
        "network is unreachable",
    )
    return "connection" in context.class_name_lower or any(
        token in context.message_lower for token in connect_tokens
    )


def _is_stream_broken(context: RecognitionContext) -> bool:
    stream_started = read_nested_value(context.exc, "stream_started")
    if stream_started:
        finish_reason = read_nested_value(context.exc, "finish_reason")
        if finish_reason in (None, ""):
            return True
    if "stream" not in context.message_lower and "stream" not in context.class_name_lower:
        return False
    return any(
        token in context.message_lower
        for token in ("broken", "closed", "incomplete", "interrupted", "connection reset")
    )
