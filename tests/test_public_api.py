import importlib
import inspect
import sys

import pytest

pytest.importorskip("pydantic")

sys.modules.pop("logicfp", None)
logicfp = importlib.import_module("logicfp")
user_mode = importlib.import_module("logicfp.user_mode")

from logicfp import create_protector, protect
from logicfp.user_mode import (
    AIErrorRecognizer,
    RecognitionContext,
    RegisteredAIErrorRecognizer,
    build_ai_error_recognition,
    ErrorActionResolverPayload,
    ErrorActionResolverResult,
    ErrorDetailsData,
    ErrorCode,
    ErrorFactData,
    LogicExecutionError,
    NormalizationError,
    ErrorPolicyData,
    ProtectRuntimeError,
    Protector,
    get_error_action,
    get_error_details,
    get_error_fact,
    get_error_policy,
    list_ai_error_recognizers,
    register_ai_error_recognizer,
    unregister_ai_error_recognizer,
)


def test_root_package_exports_user_mode_only():
    assert logicfp.__all__ == ["protect", "create_protector"]
    assert callable(protect)
    assert callable(create_protector)


def test_root_create_protector_signature_stays_user_mode_focused():
    parameters = inspect.signature(create_protector).parameters

    assert "default_source" in parameters
    assert "probe_rate" in parameters
    assert "advanced" in parameters
    assert "instance_id" not in parameters
    assert "redis_url" not in parameters


def test_root_package_protect_export_survives_submodule_import():
    importlib.import_module("logicfp.decorator")
    from logicfp import protect as exported_protect

    assert callable(exported_protect)


def test_user_mode_module_exports_advanced_user_mode_api():
    assert user_mode.__all__ == [
        "AIErrorRecognizer",
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
        "get_error_action",
        "get_error_details",
        "get_error_fact",
        "get_error_policy",
        "list_ai_error_recognizers",
        "protect",
        "register_ai_error_recognizer",
        "unregister_ai_error_recognizer",
    ]
    assert callable(user_mode.protect)
    assert callable(user_mode.create_protector)
    assert callable(user_mode.get_error_fact)
    assert callable(user_mode.get_error_policy)
    assert callable(user_mode.get_error_action)
    assert callable(user_mode.get_error_details)
    assert callable(user_mode.build_ai_error_recognition)
    assert callable(user_mode.register_ai_error_recognizer)
    assert callable(user_mode.unregister_ai_error_recognizer)
    assert callable(user_mode.list_ai_error_recognizers)
    assert user_mode.AIErrorRecognizer is AIErrorRecognizer
    assert user_mode.RecognitionContext is RecognitionContext
    assert user_mode.RegisteredAIErrorRecognizer is RegisteredAIErrorRecognizer
    assert user_mode.build_ai_error_recognition is build_ai_error_recognition
    assert user_mode.ErrorActionResolverPayload is ErrorActionResolverPayload
    assert user_mode.ErrorActionResolverResult is ErrorActionResolverResult
    assert user_mode.ErrorFactData is ErrorFactData
    assert user_mode.ErrorPolicyData is ErrorPolicyData
    assert user_mode.ErrorDetailsData is ErrorDetailsData
    assert ErrorCode is user_mode.ErrorCode
    assert LogicExecutionError is user_mode.LogicExecutionError
    assert NormalizationError is user_mode.NormalizationError
    assert ProtectRuntimeError is user_mode.ProtectRuntimeError
    assert Protector is user_mode.Protector
    assert get_error_fact is user_mode.get_error_fact
    assert get_error_policy is user_mode.get_error_policy
    assert get_error_action is user_mode.get_error_action
    assert get_error_details is user_mode.get_error_details
    assert register_ai_error_recognizer is user_mode.register_ai_error_recognizer
    assert unregister_ai_error_recognizer is user_mode.unregister_ai_error_recognizer
    assert list_ai_error_recognizers is user_mode.list_ai_error_recognizers
