from enum import Enum
from typing import Any

from .ai_error_recognizer import (
    AIErrorClassifier,
    AIErrorRecognizer,
    build_ai_error_recognition,
    recognize_ai_error,
)
from .error_report import ErrorActionResolver, ErrorPolicyResolver, build_error_report

class ErrorCode(str, Enum):
    ERR_TIMEOUT = "ERR_TIMEOUT"
    ERR_NULL = "ERR_NULL"
    ERR_NORM = "ERR_NORM"
    ERR_LOGIC = "ERR_LOGIC"
    ERR_EXECUTION_BLOCKED = "ERR_EXECUTION_BLOCKED"
    ERR_UNKNOWN = "ERR_UNKNOWN"
    ERR_HANDLER_NOT_FOUND = "ERR_HANDLER_NOT_FOUND"
    ERR_VALIDATION = "ERR_VALIDATION"
    ERR_OUTPUT_VALIDATION = "ERR_OUTPUT_VALIDATION"

class LogicFingerprintError(Exception):
    code: ErrorCode = ErrorCode.ERR_UNKNOWN
    def __init__(self, message: str = "", details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message or self.__class__.__name__
        self.details = details or {}

class TimeoutErrorLF(LogicFingerprintError):
    code = ErrorCode.ERR_TIMEOUT

class NullResultError(LogicFingerprintError):
    code = ErrorCode.ERR_NULL

class NormalizationError(LogicFingerprintError):
    code = ErrorCode.ERR_NORM

class LogicExecutionError(LogicFingerprintError):
    code = ErrorCode.ERR_LOGIC

class HandlerNotFoundError(LogicFingerprintError):
    code = ErrorCode.ERR_HANDLER_NOT_FOUND

class ValidationErrorLF(LogicFingerprintError):
    code = ErrorCode.ERR_VALIDATION

class OutputValidationErrorLF(LogicFingerprintError):
    code = ErrorCode.ERR_OUTPUT_VALIDATION

def classify_exception(exc: Exception) -> ErrorCode:
    if isinstance(exc, LogicFingerprintError):
        return exc.code
    if isinstance(exc, TimeoutError):
        return ErrorCode.ERR_TIMEOUT
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return ErrorCode.ERR_NORM
    if isinstance(exc, (AssertionError, RuntimeError)):
        return ErrorCode.ERR_LOGIC
    return ErrorCode.ERR_UNKNOWN


def build_error_details(
    exc: Exception,
    *,
    stage_hint: str | None = None,
    ai_error_classifier: AIErrorClassifier | None = None,
    ai_error_recognizers: list[AIErrorRecognizer] | tuple[AIErrorRecognizer, ...] | None = None,
    error_action_resolver: ErrorActionResolver | None = None,
) -> dict[str, Any]:
    details = dict(exc.details) if isinstance(exc, LogicFingerprintError) else {}
    if "ai_error" not in details:
        ai_error = _recognize_logicfp_ai_error(exc) or recognize_ai_error(
            exc,
            model_classifier=ai_error_classifier,
            recognizers=ai_error_recognizers,
        )
        if ai_error is not None:
            details["ai_error"] = ai_error.as_dict()

    report = build_error_report(
        code=classify_exception(exc).value,
        message=str(exc),
        stage_hint=stage_hint,
        details=details,
        action_resolver=error_action_resolver,
    )
    details["error_fact"] = report.fact.as_dict()
    details["error_policy"] = report.policy.as_dict()
    return details


def _recognize_logicfp_ai_error(exc: Exception):
    if isinstance(exc, TimeoutErrorLF):
        return build_ai_error_recognition(
            "NET_TIMEOUT",
            matched_signals=("logicfp_timeout",),
            details=dict(exc.details),
        )
    if isinstance(exc, NullResultError):
        return build_ai_error_recognition(
            "EMPTY_RESULT",
            matched_signals=("logicfp_empty_result",),
            details=dict(exc.details),
        )
    if isinstance(exc, ValidationErrorLF):
        return build_ai_error_recognition(
            "INPUT_INVALID",
            matched_signals=("logicfp_validation",),
            details=dict(exc.details),
        )
    if isinstance(exc, OutputValidationErrorLF):
        return build_ai_error_recognition(
            "OUTPUT_SCHEMA_INVALID",
            matched_signals=("logicfp_output_validation",),
            details=dict(exc.details),
        )
    return None
