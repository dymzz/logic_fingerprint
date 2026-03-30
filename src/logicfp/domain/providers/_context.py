from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any


@dataclass(frozen=True)
class RecognitionContext:
    exc: Exception
    message: str
    message_lower: str
    module_lower: str
    class_name_lower: str
    provider: str | None
    model: str | None
    status_code: int | None
    provider_code: str | None
    retry_after_s: float | int | None
    base_details: dict[str, Any]


def build_recognition_context(exc: Exception) -> RecognitionContext:
    message = exception_message(exc)
    module_lower = exc.__class__.__module__.lower()
    message_lower = message.lower()
    status_code = read_status_code(exc)
    provider_code = read_provider_code(exc)
    retry_after_s = read_retry_after(exc)
    return RecognitionContext(
        exc=exc,
        message=message,
        message_lower=message_lower,
        module_lower=module_lower,
        class_name_lower=exc.__class__.__name__.lower(),
        provider=detect_provider(module_lower, message_lower),
        model=read_nested_value(exc, "model", "model_name", "model_id"),
        status_code=status_code,
        provider_code=provider_code,
        retry_after_s=retry_after_s,
        base_details=compact_details(
            http_status=status_code,
            provider_code=provider_code,
            provider_type=module_lower or None,
            provider_request_id=read_nested_value(exc, "request_id", "provider_request_id", "request-id", "x-request-id"),
            retry_after_s=retry_after_s,
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
            raw_error_type=exc.__class__.__name__,
            raw_error_message=message,
        ),
    )


def exception_message(exc: Exception) -> str:
    message = getattr(exc, "message", None)
    if isinstance(message, str) and message:
        return message
    nested_message = read_nested_value(exc, "message", "error_message", "detail")
    if isinstance(nested_message, str) and nested_message:
        return nested_message
    return str(exc)


def detect_provider(module_lower: str, message_lower: str) -> str | None:
    if "langchain" in module_lower:
        if "openai" in message_lower:
            return "langchain-openai"
        return "langchain"
    if "google" in module_lower or "genai" in module_lower or "gemini" in module_lower or "vertexai" in module_lower:
        return "google"
    if "azure" in message_lower and ("openai" in module_lower or "openai" in message_lower):
        return "azure-openai"
    if "openai" in module_lower or "openai" in message_lower:
        return "openai"
    if "anthropic" in module_lower or "anthropic" in message_lower:
        return "anthropic"
    return None


def read_first_attr(obj: Any, *names: str) -> Any:
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return None


def read_nested_value(obj: Any, *names: str) -> Any:
    seen: set[int] = set()
    for candidate in _iter_candidate_containers(obj, seen):
        for name in names:
            if isinstance(candidate, Mapping):
                value = candidate.get(name)
            else:
                value = getattr(candidate, name, None)
            if value is not None:
                return value
    return None


def coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def read_status_code(exc: Exception) -> int | None:
    value = read_nested_value(exc, "status_code", "http_status", "status")
    return value if isinstance(value, int) else None


def read_provider_code(exc: Exception) -> str | None:
    value = read_nested_value(exc, "code", "error_code", "provider_code", "type")
    return value if isinstance(value, str) and value else None


def read_retry_after(exc: Exception) -> float | int | None:
    value = read_nested_value(exc, "retry_after", "retry_after_s")
    if isinstance(value, (int, float)):
        return value

    headers = read_nested_value(exc, "headers")
    if hasattr(headers, "get"):
        for key in ("retry-after", "Retry-After"):
            retry_after = headers.get(key)
            if retry_after is not None:
                try:
                    return float(retry_after)
                except (TypeError, ValueError):
                    return None
    return None


def compact_details(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def _iter_candidate_containers(obj: Any, seen: set[int]):
    if obj is None:
        return
    obj_id = id(obj)
    if obj_id in seen:
        return
    seen.add(obj_id)
    yield obj

    if isinstance(obj, Mapping):
        for key in ("error", "body", "response", "headers", "data", "choices", "content", "content_blocks", "results", "output"):
            value = obj.get(key)
            if value is not None:
                yield from _iter_candidate_containers(value, seen)
        return

    for attr_name in ("response", "body", "error", "headers", "data"):
        value = getattr(obj, attr_name, None)
        if value is not None:
            yield from _iter_candidate_containers(value, seen)

    if isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        for item in obj:
            if item is not None:
                yield from _iter_candidate_containers(item, seen)
