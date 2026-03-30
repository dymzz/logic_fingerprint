from __future__ import annotations

from ..ai_error_recognizer import AIErrorRecognition, build_ai_error_recognition
from ._context import RecognitionContext


def recognize_anthropic_error(context: RecognitionContext) -> AIErrorRecognition | None:
    if not _is_anthropic_context(context):
        return None

    if _is_quota_exhausted(context):
        return build_ai_error_recognition(
            "QUOTA_EXHAUSTED",
            provider="anthropic",
            model=context.model,
            matched_signals=("quota_exhausted",),
            details=context.base_details,
        )

    if _is_model_not_found(context):
        return build_ai_error_recognition(
            "MODEL_NOT_FOUND",
            provider="anthropic",
            model=context.model,
            matched_signals=("model_not_found",),
            details=context.base_details,
        )

    if _is_context_too_long(context):
        return build_ai_error_recognition(
            "CONTEXT_TOO_LONG",
            provider="anthropic",
            model=context.model,
            matched_signals=("context_too_long",),
            details=context.base_details,
        )

    if _is_token_rate_limit(context):
        return build_ai_error_recognition(
            "RATE_LIMIT_TOKEN",
            provider="anthropic",
            model=context.model,
            matched_signals=("http_429", "token_rate_limit"),
            details=context.base_details,
        )

    if _is_request_rate_limit(context):
        return build_ai_error_recognition(
            "RATE_LIMIT_REQUEST",
            provider="anthropic",
            model=context.model,
            matched_signals=("http_429", "request_rate_limit"),
            details=context.base_details,
        )

    if _is_auth_invalid(context):
        return build_ai_error_recognition(
            "AUTH_INVALID",
            provider="anthropic",
            model=context.model,
            matched_signals=("auth_invalid",),
            details=context.base_details,
        )

    if _is_auth_forbidden(context):
        return build_ai_error_recognition(
            "AUTH_FORBIDDEN",
            provider="anthropic",
            model=context.model,
            matched_signals=("auth_forbidden",),
            details=context.base_details,
        )

    if _is_upstream_overloaded(context):
        return build_ai_error_recognition(
            "UPSTREAM_OVERLOADED",
            provider="anthropic",
            model=context.model,
            matched_signals=("upstream_overloaded",),
            details=context.base_details,
        )

    if _is_upstream_5xx(context):
        return build_ai_error_recognition(
            "UPSTREAM_5XX",
            provider="anthropic",
            model=context.model,
            matched_signals=("upstream_5xx",),
            details=context.base_details,
        )

    return None


def _is_anthropic_context(context: RecognitionContext) -> bool:
    return context.provider == "anthropic" or "anthropic" in context.module_lower


def _provider_code_lower(context: RecognitionContext) -> str:
    return (context.provider_code or "").lower()


def _class_name_lower(context: RecognitionContext) -> str:
    return context.class_name_lower


def _is_quota_exhausted(context: RecognitionContext) -> bool:
    code = _provider_code_lower(context)
    return any(
        token in context.message_lower or token in code
        for token in ("insufficient_quota", "quota exceeded", "credit balance", "billing")
    )


def _is_model_not_found(context: RecognitionContext) -> bool:
    code = _provider_code_lower(context)
    class_name = _class_name_lower(context)
    if context.status_code == 404 and "model" in context.message_lower:
        return True
    return any(token in code for token in ("model_not_found", "not_found_error")) or "notfounderror" in class_name


def _is_context_too_long(context: RecognitionContext) -> bool:
    code = _provider_code_lower(context)
    if context.status_code == 400 and "context" in context.message_lower and "long" in context.message_lower:
        return True
    return any(
        token in context.message_lower or token in code
        for token in ("context length exceeded", "prompt is too long", "too many tokens", "maximum context")
    )


def _is_token_rate_limit(context: RecognitionContext) -> bool:
    if context.status_code != 429 and "ratelimiterror" not in _class_name_lower(context):
        return False
    code = _provider_code_lower(context)
    return any(
        token in context.message_lower or token in code
        for token in ("token", "tpm", "throughput", "input tokens per minute", "output tokens per minute")
    )


def _is_request_rate_limit(context: RecognitionContext) -> bool:
    if context.status_code != 429 and "ratelimiterror" not in _class_name_lower(context):
        return False
    if _is_token_rate_limit(context):
        return False
    code = _provider_code_lower(context)
    return any(
        token in context.message_lower or token in code or token in _class_name_lower(context)
        for token in ("rate limit", "requests per minute", "too many requests", "request limit", "ratelimiterror")
    )


def _is_auth_invalid(context: RecognitionContext) -> bool:
    code = _provider_code_lower(context)
    class_name = _class_name_lower(context)
    if context.status_code == 401 or "authenticationerror" in class_name:
        return True
    return any(
        token in context.message_lower or token in code
        for token in ("invalid api key", "missing api key", "authentication failed", "unauthorized")
    )


def _is_auth_forbidden(context: RecognitionContext) -> bool:
    code = _provider_code_lower(context)
    class_name = _class_name_lower(context)
    if context.status_code == 403 or "permissiondeniederror" in class_name:
        return True
    return any(
        token in context.message_lower or token in code
        for token in ("permission denied", "forbidden", "not allowed")
    )


def _is_upstream_overloaded(context: RecognitionContext) -> bool:
    code = _provider_code_lower(context)
    class_name = _class_name_lower(context)
    if context.status_code in {503, 529}:
        return True
    return any(
        token in context.message_lower or token in code or token in class_name
        for token in ("overloaded", "temporarily unavailable", "service unavailable", "internalservererror")
    )


def _is_upstream_5xx(context: RecognitionContext) -> bool:
    return context.status_code in {500, 502, 504}
