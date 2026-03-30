from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from logicfp import decorator_impl
from logicfp.domain.models import HandlerRequest
from logicfp import create_protector
from logicfp.infra.logging import NullEventLogger, PrintEventLogger
from logicfp.user_mode import (
    build_ai_error_recognition,
    ErrorCode,
    LogicExecutionError,
    ProtectRuntimeError,
    get_error_action,
    get_error_fact,
    get_error_policy,
)


def test_protect_supports_async_functions():
    protector = create_protector()

    @protector.protect(simple=False)
    async def guarded(request: HandlerRequest):
        return {"doubled": request.payload["value"] * 2}

    result = asyncio.run(guarded(payload={"value": 21}))

    assert result["ok"] is True
    assert result["result"]["doubled"] == 42


def test_create_protector_reads_project_yaml_config_file(monkeypatch, tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        """
logicfp:
  instance_id: user-mode-node
  default_source: langchain
  probe_rate: 0.33
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)

    protector = create_protector()

    assert protector.settings.instance_id == "user-mode-node"
    assert protector.settings.default_source == "langchain"
    assert protector.config.probe_rate == 0.33


def test_root_protect_creates_isolated_default_protectors():
    root_protect = importlib.import_module("logicfp").__dict__["protect"]

    @root_protect(simple=True)
    def always_fail(request: HandlerRequest):
        raise ValueError("boom")

    @root_protect(simple=False)
    def still_runs(request: HandlerRequest):
        return {"value": request.payload["value"] * 2}

    with pytest.raises(Exception, match="boom"):
        always_fail(payload={"value": 1})

    result = still_runs(payload={"value": 21})

    assert result["ok"] is True
    assert result["result"]["value"] == 42


def test_create_protector_uses_silent_logger_by_default(capsys):
    protector = create_protector()

    @protector.protect(simple=True)
    def guarded(request: HandlerRequest):
        return {"value": request.payload["value"] + 1}

    assert isinstance(protector.event_logger, NullEventLogger)
    assert guarded(payload={"value": 1}) == {"value": 2}
    captured = capsys.readouterr()
    assert captured.out == ""


def test_create_protector_accepts_explicit_event_logger():
    logger = PrintEventLogger()
    protector = create_protector(event_logger=logger)

    assert protector.event_logger is logger


def test_create_protector_accepts_advanced_dict_for_advanced_controls():
    protector = create_protector(
        advanced={
            "instance_id": "advanced-node",
        }
    )

    assert protector.settings.instance_id == "advanced-node"


def test_create_protector_warns_on_direct_advanced_arguments():
    with pytest.warns(DeprecationWarning, match="advanced arguments directly"):
        protector = create_protector(instance_id="legacy-advanced-node")

    assert protector.settings.instance_id == "legacy-advanced-node"


def test_create_protector_rejects_unknown_advanced_argument():
    with pytest.raises(TypeError, match="Unsupported create_protector\\(\\) advanced arguments"):
        create_protector(not_a_real_option=True)


def test_protect_validates_input_once_per_sync_call(monkeypatch):
    protector = create_protector()
    validate_calls = 0
    original_validate_input = decorator_impl.validate_input

    def counting_validate_input(*args, **kwargs):
        nonlocal validate_calls
        validate_calls += 1
        return original_validate_input(*args, **kwargs)

    monkeypatch.setattr(decorator_impl, "validate_input", counting_validate_input)

    @protector.protect(simple=True)
    def guarded(request: HandlerRequest):
        return {"value": request.payload["value"] + 1}

    assert guarded(payload={"value": 1}) == {"value": 2}
    assert validate_calls == 1


def test_protect_validates_input_once_per_async_call(monkeypatch):
    protector = create_protector()
    validate_calls = 0
    original_validate_input = decorator_impl.validate_input

    def counting_validate_input(*args, **kwargs):
        nonlocal validate_calls
        validate_calls += 1
        return original_validate_input(*args, **kwargs)

    monkeypatch.setattr(decorator_impl, "validate_input", counting_validate_input)

    @protector.protect(simple=True)
    async def guarded(request: HandlerRequest):
        return {"value": request.payload["value"] + 1}

    assert asyncio.run(guarded(payload={"value": 1})) == {"value": 2}
    assert validate_calls == 1


def test_protect_runtime_error_uses_normalization_error_code():
    @create_protector().protect(simple=True)
    def guarded(request: HandlerRequest):
        raise ValueError("manual review required")

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"value": 1})

    assert exc_info.value.code == ErrorCode.ERR_NORM.value


def test_protect_runtime_error_uses_null_error_code():
    @create_protector().protect(simple=True)
    def guarded(request: HandlerRequest):
        return None

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"value": 1})

    assert exc_info.value.code == ErrorCode.ERR_NULL.value


def test_protect_runtime_error_recognizes_empty_ai_text_output():
    @create_protector().protect(simple=True)
    def guarded(request: HandlerRequest):
        return {"content": "   "}

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"value": 1})

    assert exc_info.value.code == ErrorCode.ERR_NULL.value
    assert exc_info.value.details["ai_error"]["code"] == "EMPTY_RESULT"
    assert exc_info.value.details["ai_error"]["details"]["empty_fields"] == ["content"]


def test_create_protector_supports_local_ai_error_recognizers():
    def local_recognizer(context):
        if context.class_name_lower == "runtimeerror":
            return build_ai_error_recognition(
                "UPSTREAM_OVERLOADED",
                provider="test-local",
                model=context.model,
                matched_signals=("local_protector_recognizer",),
                details=context.base_details,
            )
        return None

    protector = create_protector(
        advanced={"ai_error_recognizers": [local_recognizer]},
    )

    @protector.protect(simple=True)
    def guarded(request: HandlerRequest):
        raise RuntimeError("temporary provider overload")

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"value": 1})

    assert exc_info.value.details["ai_error"]["code"] == "UPSTREAM_OVERLOADED"
    assert exc_info.value.details["ai_error"]["provider"] == "test-local"


def test_create_protector_rejects_non_callable_local_ai_error_recognizer():
    with pytest.raises(TypeError, match="ai_error_recognizers"):
        create_protector(advanced={"ai_error_recognizers": ["not-callable"]})


def test_protect_runtime_error_uses_input_validation_error_code():
    from pydantic import BaseModel

    class InputModel(BaseModel):
        quantity: int

    protector = create_protector()

    @protector.protect(input_model=InputModel, simple=True)
    def guarded(request: HandlerRequest):
        return {"value": request.payload["quantity"]}

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"quantity": "bad"})

    assert exc_info.value.code == ErrorCode.ERR_VALIDATION.value
    assert "errors" in exc_info.value.details
    assert protector.metrics.success_requests == 0
    assert protector.metrics.failed_requests == 1
    assert protector.metrics.failed_by_code[ErrorCode.ERR_VALIDATION.value] == 1
    assert protector.metrics.failed_by_stage["input"] == 1
    assert protector.metrics.failed_by_source["caller"] == 1
    assert protector.metrics.failed_by_action["block"] == 1


def test_protect_runtime_error_uses_output_validation_error_code():
    from pydantic import BaseModel

    class OutputModel(BaseModel):
        value: int

    protector = create_protector()

    @protector.protect(output_model=OutputModel, simple=True)
    def guarded(request: HandlerRequest):
        return {"value": "bad"}

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"value": 1})

    assert exc_info.value.code == ErrorCode.ERR_OUTPUT_VALIDATION.value
    assert "errors" in exc_info.value.details
    assert protector.metrics.success_requests == 0
    assert protector.metrics.failed_requests == 1


def test_blocked_request_records_dimension_metrics():
    protector = create_protector()

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        return {"value": request.payload["value"] + 1}

    protector.fsm.record_hard_fail("manual-open")

    result = guarded(payload={"value": 1})

    assert result["ok"] is False
    assert result["error"]["code"] == ErrorCode.ERR_EXECUTION_BLOCKED.value
    assert protector.metrics.blocked_requests == 1
    assert protector.metrics.blocked_by_code[ErrorCode.ERR_EXECUTION_BLOCKED.value] == 1
    assert protector.metrics.blocked_by_stage["execute"] == 1
    assert protector.metrics.blocked_by_source["system"] == 1
    assert protector.metrics.blocked_by_action["trip"] == 1


def test_simple_false_success_envelope_shape():
    @create_protector().protect(simple=False)
    def guarded(request: HandlerRequest):
        return {"value": request.payload["value"] + 1}

    result = guarded(payload={"value": 1})

    assert set(result) == {"ok", "result", "context"}
    assert result["ok"] is True
    assert result["result"] == {"value": 2}
    assert set(result["context"]) == {
        "request_id",
        "trace_id",
        "user_id",
        "source",
        "timestamp",
        "headers",
        "metadata",
    }
    assert result["context"]["request_id"] is not None
    assert result["context"]["trace_id"] is not None


def test_simple_false_failure_envelope_shape():
    @create_protector().protect(simple=False)
    def guarded(request: HandlerRequest):
        raise LogicExecutionError("manual review required")

    result = guarded(payload={"value": 1})

    assert set(result) == {"ok", "error", "context"}
    assert result["ok"] is False
    assert set(result["error"]) == {"code", "message", "details"}
    assert result["error"]["code"] == ErrorCode.ERR_LOGIC.value
    assert result["error"]["message"] == "manual review required"
    assert "error_fact" in result["error"]["details"]
    assert "error_policy" in result["error"]["details"]
    assert result["error"]["details"]["error_fact"]["stage"] == "execute"
    assert result["error"]["details"]["error_policy"]["action"] == "block"
    assert set(result["context"]) == {
        "request_id",
        "trace_id",
        "user_id",
        "source",
        "timestamp",
        "headers",
        "metadata",
    }


def test_simple_false_validation_failure_uses_same_error_envelope_shape():
    from pydantic import BaseModel

    class InputModel(BaseModel):
        quantity: int

    @create_protector().protect(input_model=InputModel, simple=False)
    def guarded(request: HandlerRequest):
        return {"value": request.payload["quantity"]}

    result = guarded(payload={"quantity": "bad"})

    assert set(result) == {"ok", "error", "context"}
    assert result["ok"] is False
    assert set(result["error"]) == {"code", "message", "details"}
    assert result["error"]["code"] == ErrorCode.ERR_VALIDATION.value
    assert result["error"]["message"] == "Input validation failed."
    assert "errors" in result["error"]["details"]


def test_user_mode_error_helpers_read_simple_true_error() -> None:
    @create_protector().protect(simple=True)
    def guarded(request: HandlerRequest):
        raise LogicExecutionError("manual review required")

    with pytest.raises(ProtectRuntimeError) as exc_info:
        guarded(payload={"value": 1})

    fact = get_error_fact(exc_info.value)
    policy = get_error_policy(exc_info.value)

    assert fact is not None
    assert policy is not None
    assert fact["stage"] == "execute"
    assert fact["source"] == "system"
    assert fact["recoverability"] == "non_recoverable"
    assert get_error_action(exc_info.value) == "block"


def test_user_mode_error_helpers_read_simple_false_error_envelope() -> None:
    @create_protector().protect(simple=False)
    def guarded(request: HandlerRequest):
        raise LogicExecutionError("manual review required")

    result = guarded(payload={"value": 1})

    fact = get_error_fact(result["error"])
    policy = get_error_policy(result)

    assert fact is not None
    assert policy is not None
    assert fact["stage"] == "execute"
    assert fact["source"] == "system"
    assert fact["recoverability"] == "non_recoverable"
    assert get_error_action(result) == "block"
