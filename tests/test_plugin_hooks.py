from __future__ import annotations

import pytest

pytest.importorskip("pydantic")

from logicfp import create_protector
from logicfp.app_factory import create_demo_app
from logicfp.domain.models import HandlerRequest
from logicfp.plugins import (
    ActionRisk,
    CredibilityResult,
    DecisionType,
    FinalDecision,
    HookDecision,
    SuccessHook,
    SUPPORTED_HOOK_CONTRACT_VERSION,
)
from logicfp.runtime import build_demo_runtime


class CredibilityPlugin(SuccessHook):
    def after_success(self, request, result):
        assert request.action_risk is ActionRisk.HIGH
        assert request.decision_type is DecisionType.ACTION
        return HookDecision(
            credibility=CredibilityResult(
                confidence=0.42,
                risk_level="medium",
                verdict="warn",
                reasons=["missing citations"],
            ),
            final_decision=FinalDecision.WARN,
            plugin_meta={"plugin_version": "0.1.0"},
        )


class ExplodingPlugin(SuccessHook):
    def after_success(self, request, result):
        raise RuntimeError("plugin exploded")


def test_hook_contract_version_is_public():
    assert SUPPORTED_HOOK_CONTRACT_VERSION == "1.0.0"


def test_runtime_success_hook_merges_plugin_meta():
    runtime = build_demo_runtime(success_hooks=[CredibilityPlugin()])
    request = HandlerRequest(
        payload={
            "numbers": [1, 2, 3],
            "action_risk": "high",
            "decision_type": "action",
        }
    )

    outcome = runtime.middleware.execute_handler("sum_numbers", request=request)

    assert outcome.succeeded is True
    assert outcome.result.data["sum"] == 6
    assert outcome.result.meta["decision"] == "warn"
    assert outcome.result.meta["credibility"]["confidence"] == 0.42
    assert outcome.result.meta["plugin_decisions"][0]["hook"] == "CredibilityPlugin"


def test_runtime_success_hook_is_fail_open_by_default():
    runtime = build_demo_runtime(success_hooks=[ExplodingPlugin()])

    outcome = runtime.middleware.execute_handler(
        "sum_numbers",
        request=HandlerRequest(payload={"numbers": [1, 2, 3]}),
    )

    assert outcome.succeeded is True
    assert outcome.result.data["sum"] == 6
    assert outcome.result.meta == {}


def test_api_success_hook_exposes_local_plugin_meta():
    from fastapi.testclient import TestClient

    runtime = build_demo_runtime(success_hooks=[CredibilityPlugin()])
    client = TestClient(create_demo_app(runtime=runtime))

    response = client.post(
        "/execute_handler",
        json={
            "handler": "sum_numbers",
            "payload": {
                "numbers": [1, 2],
                "action_risk": "high",
                "decision_type": "action",
            },
        },
    )

    body = response.json()
    assert body["ok"] is True
    assert body["result"]["meta"]["decision"] == "warn"


def test_protector_success_hook_merges_meta_for_dict_results():
    protector = create_protector(
        advanced={"success_hooks": [CredibilityPlugin()]},
    )

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        return {
            "content": "ok",
            "action_risk": "ignored-in-output",
        }

    result = guarded(
        payload={
            "prompt": "can I do this?",
            "action_risk": "high",
            "decision_type": "action",
        }
    )

    assert result["ok"] is True
    assert result["result"]["meta"]["decision"] == "warn"


def test_protector_fail_closed_turns_plugin_error_into_failure():
    protector = create_protector(
        advanced={
            "success_hooks": [ExplodingPlugin()],
            "plugin_failure_mode": "fail_closed",
        }
    )

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        return {"value": 1}

    result = guarded(payload={"value": 1})

    assert result["ok"] is False
    assert result["error"]["code"] == "ERR_LOGIC"
    assert result["error"]["details"]["error_fact"]["stage"] == "plugin"
