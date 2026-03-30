from .decorator_impl import ProtectRuntimeError, Protector, create_protector, protect
from .domain.ai_error_recognizer import (
    AIErrorRecognizer,
    RegisteredAIErrorRecognizer,
    build_ai_error_recognition,
    list_ai_error_recognizers,
    register_ai_error_recognizer,
    unregister_ai_error_recognizer,
)
from .domain.error_report import ErrorActionResolverPayload, ErrorActionResolverResult
from .domain.errors import ErrorCode, LogicExecutionError, NormalizationError
from .error_access import (
    AIErrorData,
    ErrorDetailsData,
    ErrorFactData,
    ErrorPolicyData,
    get_ai_error,
    get_error_action,
    get_error_details,
    get_error_fact,
    get_error_policy,
)
from .domain.providers._context import RecognitionContext

__all__ = [
    "AIErrorRecognizer",
    "AIErrorData",
    "RecognitionContext",
    "RegisteredAIErrorRecognizer",
    "build_ai_error_recognition",
    "ErrorActionResolverPayload",
    "ErrorActionResolverResult",
    "ErrorDetailsData",
    "ErrorCode",
    "ErrorFactData",
    "LogicExecutionError",
    "NormalizationError",
    "ErrorPolicyData",
    "ProtectRuntimeError",
    "Protector",
    "create_protector",
    "get_ai_error",
    "get_error_action",
    "get_error_details",
    "get_error_fact",
    "get_error_policy",
    "list_ai_error_recognizers",
    "protect",
    "register_ai_error_recognizer",
    "unregister_ai_error_recognizer",
]
