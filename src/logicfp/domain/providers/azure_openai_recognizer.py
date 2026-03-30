from __future__ import annotations

from ..ai_error_recognizer import AIErrorRecognition, build_ai_error_recognition
from ._context import RecognitionContext


def recognize_azure_openai_error(context: RecognitionContext) -> AIErrorRecognition | None:
    if not _is_azure_openai_context(context):
        return None

    if _is_content_filter(context):
        return build_ai_error_recognition(
            "SAFETY_REFUSAL",
            provider="azure-openai",
            model=context.model,
            matched_signals=("azure_content_filter",),
            details=context.base_details,
        )

    if _is_deployment_not_found(context):
        return build_ai_error_recognition(
            "MODEL_NOT_FOUND",
            provider="azure-openai",
            model=context.model,
            matched_signals=("azure_deployment_not_found",),
            details=context.base_details,
        )

    if _is_context_too_long(context):
        return build_ai_error_recognition(
            "CONTEXT_TOO_LONG",
            provider="azure-openai",
            model=context.model,
            matched_signals=("context_too_long",),
            details=context.base_details,
        )

    if _is_token_rate_limit(context):
        return build_ai_error_recognition(
            "RATE_LIMIT_TOKEN",
            provider="azure-openai",
            model=context.model,
            matched_signals=("http_429", "token_rate_limit"),
            details=context.base_details,
        )

    if _is_request_rate_limit(context):
        return build_ai_error_recognition(
            "RATE_LIMIT_REQUEST",
            provider="azure-openai",
            model=context.model,
            matched_signals=("http_429", "request_rate_limit"),
            details=context.base_details,
        )

    if _is_auth_invalid(context):
        return build_ai_error_recognition(
            "AUTH_INVALID",
            provider="azure-openai",
            model=context.model,
            matched_signals=("auth_invalid",),
            details=context.base_details,
        )

    if _is_upstream_overloaded(context):
        return build_ai_error_recognition(
            "UPSTREAM_OVERLOADED",
            provider="azure-openai",
            model=context.model,
            matched_signals=("upstream_overloaded",),
            details=context.base_details,
        )

    if _is_upstream_5xx(context):
        return build_ai_error_recognition(
            "UPSTREAM_5XX",
            provider="azure-openai",
            model=context.model,
            matched_signals=("upstream_5xx",),
            details=context.base_details,
        )

    return None


def _is_azure_openai_context(context: RecognitionContext) -> bool:
    return "azure" in context.message_lower or "azure" in context.module_lower


def _provider_code_lower(context: RecognitionContext) -> str:
    return (context.provider_code or "").lower()


def _is_content_filter(context: RecognitionContext) -> bool:
    code = _provider_code_lower(context)
    return any(
        token in context.message_lower or token in code
        for token in ("content_filter", "content filter", "responsible_ai", "responsibleaipolicy")
    )


def _is_deployment_not_found(context: RecognitionContext) -> bool:
    if context.status_code == 404:
        return True
    return any(
        token in context.message_lower
        for token in ("deployment not found", "resource not found", "the api deployment")
    )


def _is_context_too_long(context: RecognitionContext) -> bool:
    return any(
        token in context.message_lower
        for token in ("context length exceeded", "maximum context length", "too many tokens", "token limit")
    )


def _is_token_rate_limit(context: RecognitionContext) -> bool:
    if context.status_code != 429:
        return False
    return any(
        token in context.message_lower
        for token in ("token", "tpm", "throughput", "tokens per minute")
    )


def _is_request_rate_limit(context: RecognitionContext) -> bool:
    if context.status_code != 429:
        return False
    if _is_token_rate_limit(context):
        return False
    return any(
        token in context.message_lower
        for token in ("rate limit", "requests per minute", "too many requests", "retry after")
    )


def _is_auth_invalid(context: RecognitionContext) -> bool:
    if context.status_code == 401:
        return True
    return any(
        token in context.message_lower
        for token in ("invalid api key", "access denied", "unauthorized")
    )


def _is_upstream_overloaded(context: RecognitionContext) -> bool:
    if context.status_code in {503, 529}:
        return True
    return any(
        token in context.message_lower
        for token in ("overloaded", "temporarily unavailable", "server busy")
    )


def _is_upstream_5xx(context: RecognitionContext) -> bool:
    return context.status_code in {500, 502, 504}
