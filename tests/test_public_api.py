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
    ErrorCode,
    LogicExecutionError,
    NormalizationError,
    ProtectRuntimeError,
    Protector,
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
        "ErrorCode",
        "LogicExecutionError",
        "NormalizationError",
        "ProtectRuntimeError",
        "Protector",
        "create_protector",
        "protect",
    ]
    assert callable(user_mode.protect)
    assert callable(user_mode.create_protector)
    assert ErrorCode is user_mode.ErrorCode
    assert LogicExecutionError is user_mode.LogicExecutionError
    assert NormalizationError is user_mode.NormalizationError
    assert ProtectRuntimeError is user_mode.ProtectRuntimeError
    assert Protector is user_mode.Protector
