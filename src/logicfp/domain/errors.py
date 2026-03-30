from enum import Enum

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
