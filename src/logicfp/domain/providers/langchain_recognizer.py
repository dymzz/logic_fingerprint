from __future__ import annotations

from ..ai_error_recognizer import AIErrorRecognition, build_ai_error_recognition
from ._context import RecognitionContext, read_first_attr


def recognize_langchain_error(context: RecognitionContext) -> AIErrorRecognition | None:
    if "langchain" not in context.module_lower:
        return None

    provider = context.provider or "langchain"

    if _is_output_parse_error(context):
        return build_ai_error_recognition(
            "OUTPUT_PARSE_ERROR",
            provider=provider,
            model=context.model,
            matched_signals=("langchain_output_parser",),
            details=context.base_details,
        )

    if _is_tool_args_invalid(context):
        return build_ai_error_recognition(
            "TOOL_ARGS_INVALID",
            provider=provider,
            model=context.model,
            matched_signals=("langchain_tool_args_invalid",),
            details=context.base_details,
        )

    if _is_tool_not_found(context):
        return build_ai_error_recognition(
            "TOOL_NOT_FOUND",
            provider=provider,
            model=context.model,
            matched_signals=("langchain_tool_not_found",),
            details=context.base_details,
        )

    if _is_tool_exec_error(context):
        return build_ai_error_recognition(
            "TOOL_EXEC_ERROR",
            provider=provider,
            model=context.model,
            matched_signals=("langchain_tool_exception",),
            details=context.base_details,
        )

    if _is_stream_broken(context):
        return build_ai_error_recognition(
            "STREAM_BROKEN",
            provider=provider,
            model=context.model,
            matched_signals=("langchain_stream_broken",),
            details=context.base_details,
        )

    return None


def _is_output_parse_error(context: RecognitionContext) -> bool:
    if "outputparserexception" in context.class_name_lower:
        return True
    return "could not parse" in context.message_lower or "failed to parse" in context.message_lower


def _is_tool_args_invalid(context: RecognitionContext) -> bool:
    if read_first_attr(context.exc, "tool_name") and "validation" in context.class_name_lower:
        return True
    return any(
        token in context.message_lower
        for token in ("tool input validation", "invalid tool arguments", "tool args validation")
    )


def _is_tool_not_found(context: RecognitionContext) -> bool:
    return any(
        token in context.message_lower
        for token in ("tool not found", "unknown tool", "no such tool")
    )


def _is_tool_exec_error(context: RecognitionContext) -> bool:
    if "toolexception" in context.class_name_lower:
        return True
    return "tool exception" in context.message_lower or "tool execution failed" in context.message_lower


def _is_stream_broken(context: RecognitionContext) -> bool:
    stream_started = read_first_attr(context.exc, "stream_started")
    if stream_started:
        finish_reason = read_first_attr(context.exc, "finish_reason")
        if finish_reason in (None, ""):
            return True
    if "stream" not in context.message_lower and "stream" not in context.class_name_lower:
        return False
    return any(
        token in context.message_lower
        for token in ("broken", "closed", "incomplete", "interrupted", "connection reset")
    )
