from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AIErrorCategory(str, Enum):
    NETWORK = "network"
    STREAM = "stream"
    CLIENT = "client"
    RATE_LIMIT = "rate_limit"
    QUOTA = "quota"
    AUTH = "auth"
    REQUEST = "request"
    UPSTREAM = "upstream"
    SAFETY = "safety"
    OUTPUT = "output"
    TOOL = "tool"
    UNKNOWN = "unknown"


class AIErrorSeverity(str, Enum):
    NOISE = "noise"
    WARN = "warn"
    BLOCK = "block"


class AIErrorPhase(str, Enum):
    PREPARE = "prepare"
    REQUEST = "request"
    STREAM = "stream"
    PARSE = "parse"
    VALIDATE = "validate"
    TOOL = "tool"
    POSTPROCESS = "postprocess"


COMMON_DIAGNOSTIC_FIELDS: tuple[str, ...] = (
    "http_status",
    "provider_code",
    "provider_type",
    "provider_request_id",
    "retry_after_s",
    "finish_reason",
    "stream_started",
    "received_chunks",
    "input_tokens",
    "output_tokens",
    "max_output_tokens",
    "tool_name",
    "tool_call_id",
    "schema_name",
    "raw_error_type",
    "raw_error_message",
)


@dataclass(frozen=True)
class AIErrorDescriptor:
    code: str
    category: AIErrorCategory
    retryable: bool | None
    severity: AIErrorSeverity
    phase: AIErrorPhase
    description: str
    recognition_signals: tuple[str, ...]
    detail_fields: tuple[str, ...] = COMMON_DIAGNOSTIC_FIELDS


AI_ERROR_CATALOG: dict[str, AIErrorDescriptor] = {
    "NET_CONNECT": AIErrorDescriptor(
        code="NET_CONNECT",
        category=AIErrorCategory.NETWORK,
        retryable=True,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.REQUEST,
        description="Connection setup failed before a usable response was received.",
        recognition_signals=("dns_failure", "tls_error", "connect_error", "connection_reset"),
    ),
    "NET_TIMEOUT": AIErrorDescriptor(
        code="NET_TIMEOUT",
        category=AIErrorCategory.NETWORK,
        retryable=True,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.REQUEST,
        description="Connect or read timeout while waiting for the model or upstream service.",
        recognition_signals=("connect_timeout", "read_timeout"),
    ),
    "STREAM_BROKEN": AIErrorDescriptor(
        code="STREAM_BROKEN",
        category=AIErrorCategory.STREAM,
        retryable=True,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.STREAM,
        description="Streaming started but ended before a normal completion signal was observed.",
        recognition_signals=("stream_started", "missing_done", "connection_lost_mid_stream"),
    ),
    "CLIENT_CANCELLED": AIErrorDescriptor(
        code="CLIENT_CANCELLED",
        category=AIErrorCategory.CLIENT,
        retryable=False,
        severity=AIErrorSeverity.NOISE,
        phase=AIErrorPhase.REQUEST,
        description="The caller cancelled the request before completion.",
        recognition_signals=("cancelled_error", "client_abort"),
    ),
    "RATE_LIMIT_REQUEST": AIErrorDescriptor(
        code="RATE_LIMIT_REQUEST",
        category=AIErrorCategory.RATE_LIMIT,
        retryable=True,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.REQUEST,
        description="The provider rejected the request because request throughput exceeded a limit.",
        recognition_signals=("http_429", "rpm_limit", "rps_limit", "request_rate_limit"),
    ),
    "RATE_LIMIT_TOKEN": AIErrorDescriptor(
        code="RATE_LIMIT_TOKEN",
        category=AIErrorCategory.RATE_LIMIT,
        retryable=True,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.REQUEST,
        description="The provider rejected the request because token throughput exceeded a limit.",
        recognition_signals=("http_429", "tpm_limit", "throughput_limit", "token_rate_limit"),
    ),
    "QUOTA_EXHAUSTED": AIErrorDescriptor(
        code="QUOTA_EXHAUSTED",
        category=AIErrorCategory.QUOTA,
        retryable=False,
        severity=AIErrorSeverity.BLOCK,
        phase=AIErrorPhase.REQUEST,
        description="Credits or quota were exhausted for the current account or project.",
        recognition_signals=("quota_exhausted", "credit_exhausted", "billing_limit"),
    ),
    "AUTH_INVALID": AIErrorDescriptor(
        code="AUTH_INVALID",
        category=AIErrorCategory.AUTH,
        retryable=False,
        severity=AIErrorSeverity.BLOCK,
        phase=AIErrorPhase.REQUEST,
        description="Authentication failed because the credential is missing or invalid.",
        recognition_signals=("http_401", "invalid_api_key", "missing_api_key"),
    ),
    "AUTH_FORBIDDEN": AIErrorDescriptor(
        code="AUTH_FORBIDDEN",
        category=AIErrorCategory.AUTH,
        retryable=False,
        severity=AIErrorSeverity.BLOCK,
        phase=AIErrorPhase.REQUEST,
        description="The caller is authenticated but does not have permission to use the resource.",
        recognition_signals=("http_403", "permission_denied", "model_forbidden"),
    ),
    "MODEL_NOT_FOUND": AIErrorDescriptor(
        code="MODEL_NOT_FOUND",
        category=AIErrorCategory.REQUEST,
        retryable=False,
        severity=AIErrorSeverity.BLOCK,
        phase=AIErrorPhase.REQUEST,
        description="The requested model or endpoint does not exist.",
        recognition_signals=("http_404", "model_not_found"),
    ),
    "INPUT_INVALID": AIErrorDescriptor(
        code="INPUT_INVALID",
        category=AIErrorCategory.REQUEST,
        retryable=False,
        severity=AIErrorSeverity.BLOCK,
        phase=AIErrorPhase.PREPARE,
        description="The request body or request parameters are invalid before execution.",
        recognition_signals=("http_400", "invalid_request", "invalid_parameters"),
    ),
    "CONTEXT_TOO_LONG": AIErrorDescriptor(
        code="CONTEXT_TOO_LONG",
        category=AIErrorCategory.REQUEST,
        retryable=False,
        severity=AIErrorSeverity.BLOCK,
        phase=AIErrorPhase.PREPARE,
        description="The input exceeds the provider or model context window.",
        recognition_signals=("context_length_exceeded", "input_too_large", "max_tokens_exceeded"),
    ),
    "UPSTREAM_OVERLOADED": AIErrorDescriptor(
        code="UPSTREAM_OVERLOADED",
        category=AIErrorCategory.UPSTREAM,
        retryable=True,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.REQUEST,
        description="The provider is overloaded or temporarily unavailable.",
        recognition_signals=("http_503", "http_529", "overloaded", "temporarily_unavailable"),
    ),
    "UPSTREAM_5XX": AIErrorDescriptor(
        code="UPSTREAM_5XX",
        category=AIErrorCategory.UPSTREAM,
        retryable=True,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.REQUEST,
        description="The provider returned a generic 5xx class server-side failure.",
        recognition_signals=("http_500", "http_502", "http_504", "gateway_error"),
    ),
    "SAFETY_REFUSAL": AIErrorDescriptor(
        code="SAFETY_REFUSAL",
        category=AIErrorCategory.SAFETY,
        retryable=False,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.PARSE,
        description="The model explicitly refused the request for safety or policy reasons.",
        recognition_signals=("refusal", "blocked_content", "safety_filter"),
    ),
    "OUTPUT_TRUNCATED": AIErrorDescriptor(
        code="OUTPUT_TRUNCATED",
        category=AIErrorCategory.OUTPUT,
        retryable=None,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.PARSE,
        description="The output ended because the generation hit a length limit.",
        recognition_signals=("finish_reason_length", "truncated_output"),
    ),
    "OUTPUT_PARSE_ERROR": AIErrorDescriptor(
        code="OUTPUT_PARSE_ERROR",
        category=AIErrorCategory.OUTPUT,
        retryable=False,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.PARSE,
        description="The model returned content that could not be parsed as the expected format.",
        recognition_signals=("json_parse_error", "structured_output_parse_error"),
    ),
    "OUTPUT_SCHEMA_INVALID": AIErrorDescriptor(
        code="OUTPUT_SCHEMA_INVALID",
        category=AIErrorCategory.OUTPUT,
        retryable=False,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.VALIDATE,
        description="The output parsed, but failed schema or pydantic validation.",
        recognition_signals=("schema_validation_error", "pydantic_validation_error"),
    ),
    "TOOL_NOT_FOUND": AIErrorDescriptor(
        code="TOOL_NOT_FOUND",
        category=AIErrorCategory.TOOL,
        retryable=False,
        severity=AIErrorSeverity.BLOCK,
        phase=AIErrorPhase.TOOL,
        description="A requested tool name was not registered or not available.",
        recognition_signals=("tool_missing", "unknown_tool_name"),
    ),
    "TOOL_ARGS_INVALID": AIErrorDescriptor(
        code="TOOL_ARGS_INVALID",
        category=AIErrorCategory.TOOL,
        retryable=False,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.TOOL,
        description="Tool invocation arguments failed validation or schema checks.",
        recognition_signals=("tool_args_validation_error", "tool_schema_error"),
    ),
    "TOOL_TIMEOUT": AIErrorDescriptor(
        code="TOOL_TIMEOUT",
        category=AIErrorCategory.TOOL,
        retryable=True,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.TOOL,
        description="The tool invocation exceeded the configured timeout.",
        recognition_signals=("tool_timeout", "subprocess_timeout"),
    ),
    "TOOL_EXEC_ERROR": AIErrorDescriptor(
        code="TOOL_EXEC_ERROR",
        category=AIErrorCategory.TOOL,
        retryable=None,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.TOOL,
        description="The tool ran but raised an execution error.",
        recognition_signals=("tool_exception", "tool_runtime_error"),
    ),
    "EMPTY_RESULT": AIErrorDescriptor(
        code="EMPTY_RESULT",
        category=AIErrorCategory.OUTPUT,
        retryable=False,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.POSTPROCESS,
        description="The call completed but produced an empty result when one was required.",
        recognition_signals=("null_result", "empty_result", "missing_content"),
    ),
    "UNKNOWN": AIErrorDescriptor(
        code="UNKNOWN",
        category=AIErrorCategory.UNKNOWN,
        retryable=None,
        severity=AIErrorSeverity.WARN,
        phase=AIErrorPhase.POSTPROCESS,
        description="Fallback bucket for failures that do not match a known recognition rule.",
        recognition_signals=("unclassified_exception",),
    ),
}


FIRST_WAVE_AI_ERROR_CODES: tuple[str, ...] = (
    "NET_TIMEOUT",
    "STREAM_BROKEN",
    "RATE_LIMIT_REQUEST",
    "RATE_LIMIT_TOKEN",
    "AUTH_INVALID",
    "UPSTREAM_OVERLOADED",
    "OUTPUT_SCHEMA_INVALID",
    "TOOL_TIMEOUT",
)


def get_ai_error_descriptor(code: str) -> AIErrorDescriptor | None:
    return AI_ERROR_CATALOG.get(code)
