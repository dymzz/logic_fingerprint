from __future__ import annotations

from ..ai_error_recognizer import AIErrorRecognition, build_ai_error_recognition
from ._context import RecognitionContext


def recognize_gemini_error(context: RecognitionContext) -> AIErrorRecognition | None:
    if not _is_gemini_context(context):
        return None

    if _is_model_not_found(context):
        return build_ai_error_recognition(
            "MODEL_NOT_FOUND",
            provider="google",
            model=context.model,
            matched_signals=("model_not_found",),
            details=context.base_details,
        )

    if _is_context_too_long(context):
        return build_ai_error_recognition(
            "CONTEXT_TOO_LONG",
            provider="google",
            model=context.model,
            matched_signals=("context_too_long",),
            details=context.base_details,
        )

    if _is_token_rate_limit(context):
        return build_ai_error_recognition(
            "RATE_LIMIT_TOKEN",
            provider="google",
            model=context.model,
            matched_signals=("http_429", "token_rate_limit"),
            details=context.base_details,
        )

    if _is_request_rate_limit(context):
        return build_ai_error_recognition(
            "RATE_LIMIT_REQUEST",
            provider="google",
            model=context.model,
            matched_signals=("http_429", "request_rate_limit"),
            details=context.base_details,
        )

    if _is_quota_exhausted(context):
        return build_ai_error_recognition(
            "QUOTA_EXHAUSTED",
            provider="google",
            model=context.model,
            matched_signals=("quota_exhausted",),
            details=context.base_details,
        )

    if _is_auth_invalid(context):
        return build_ai_error_recognition(
            "AUTH_INVALID",
            provider="google",
            model=context.model,
            matched_signals=("auth_invalid",),
            details=context.base_details,
        )

    if _is_auth_forbidden(context):
        return build_ai_error_recognition(
            "AUTH_FORBIDDEN",
            provider="google",
            model=context.model,
            matched_signals=("auth_forbidden",),
            details=context.base_details,
        )

    if _is_safety_blocked(context):
        return build_ai_error_recognition(
            "SAFETY_REFUSAL",
            provider="google",
            model=context.model,
            matched_signals=("safety_blocked",),
            details=context.base_details,
        )

    if _is_upstream_overloaded(context):
        return build_ai_error_recognition(
            "UPSTREAM_OVERLOADED",
            provider="google",
            model=context.model,
            matched_signals=("upstream_overloaded",),
            details=context.base_details,
        )

    if _is_upstream_5xx(context):
        return build_ai_error_recognition(
            "UPSTREAM_5XX",
            provider="google",
            model=context.model,
            matched_signals=("upstream_5xx",),
            details=context.base_details,
        )

    return None


def _is_gemini_context(context: RecognitionContext) -> bool:
    return (
        "google" in context.module_lower
        or "genai" in context.module_lower
        or "gemini" in context.module_lower
        or "vertexai" in context.module_lower
    )


def _provider_code_lower(context: RecognitionContext) -> str:
    return (context.provider_code or "").lower()


def _is_quota_exhausted(context: RecognitionContext) -> bool:
    code = _provider_code_lower(context)
    explicit_quota_tokens = ("quota exceeded", "billing", "insufficient_quota", "credit")
    if any(token in context.message_lower or token in code for token in explicit_quota_tokens):
        return True
    if "resource exhausted" in context.message_lower or "resourceexhausted" in context.class_name_lower:
        rate_limit_tokens = ("rate limit", "too many requests", "token", "tpm", "throughput", "requests per")
        if not any(token in context.message_lower for token in rate_limit_tokens):
            return True
    return False


def _is_model_not_found(context: RecognitionContext) -> bool:
    if context.status_code == 404 and "model" in context.message_lower:
        return True
    return any(
        token in context.message_lower
        for token in ("model not found", "not found for api version", "is not found")
    )


def _is_context_too_long(context: RecognitionContext) -> bool:
    return any(
        token in context.message_lower
        for token in (
            "context length exceeded",
            "token limit",
            "too many tokens",
            "request payload size exceeds",
            "prompt is too long",
            "maximum context",
        )
    )


def _is_token_rate_limit(context: RecognitionContext) -> bool:
    if context.status_code != 429 and "resourceexhausted" not in context.class_name_lower:
        return False
    return any(
        token in context.message_lower
        for token in ("token", "tpm", "throughput", "tokens per minute")
    )


def _is_request_rate_limit(context: RecognitionContext) -> bool:
    if context.status_code != 429 and "resourceexhausted" not in context.class_name_lower:
        return False
    if _is_token_rate_limit(context):
        return False
    if _is_quota_exhausted(context):
        return False
    return any(
        token in context.message_lower or token in context.class_name_lower
        for token in ("rate limit", "too many requests", "resource exhausted", "resourceexhausted")
    )


def _is_auth_invalid(context: RecognitionContext) -> bool:
    if context.status_code == 401:
        return True
    return any(
        token in context.message_lower
        for token in ("api key not valid", "invalid api key", "api key expired", "unauthenticated")
    )


def _is_auth_forbidden(context: RecognitionContext) -> bool:
    if context.status_code == 403:
        return True
    return any(
        token in context.message_lower
        for token in ("permission denied", "forbidden", "not allowed")
    )


def _is_safety_blocked(context: RecognitionContext) -> bool:
    return any(
        token in context.message_lower
        for token in ("safety", "blocked", "finish_reason: safety", "harm_category")
    )


def _is_upstream_overloaded(context: RecognitionContext) -> bool:
    if context.status_code in {503, 529}:
        return True
    return any(
        token in context.message_lower
        for token in ("overloaded", "temporarily unavailable", "service unavailable")
    )


def _is_upstream_5xx(context: RecognitionContext) -> bool:
    return context.status_code in {500, 502, 504}
