from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from ..domain.models import HandlerRequest, HandlerResponse
from .contracts import (
    ActionRisk,
    CredibilityResult,
    DecisionType,
    FinalDecision,
    HookDecision,
    HookRequest,
    HookResult,
    SuccessHook,
)


class PluginExecutionError(RuntimeError):
    pass


def run_success_hooks(
    request: HookRequest,
    result: HookResult,
    hooks: Iterable[SuccessHook],
    *,
    plugin_failure_mode: str = "fail_open",
) -> tuple[HookResult, list[HookDecision]]:
    normalized_mode = _normalize_plugin_failure_mode(plugin_failure_mode)
    merged_result = HookResult(
        ok=result.ok,
        output=result.output,
        meta=dict(result.meta),
    )
    decisions: list[HookDecision] = []

    for hook in hooks:
        try:
            decision = hook.after_success(request, merged_result)
        except Exception as exc:
            if normalized_mode == "fail_closed":
                raise PluginExecutionError(
                    f"Success hook '{_hook_name(hook)}' failed."
                ) from exc
            continue
        if decision is None:
            continue
        decisions.append(decision)
        _merge_decision_into_result(
            merged_result,
            decision=decision,
            hook_name=_hook_name(hook),
        )

    return merged_result, decisions


def apply_success_hooks(
    *,
    request: HandlerRequest,
    result: Any,
    hooks: Iterable[SuccessHook],
    plugin_failure_mode: str = "fail_open",
) -> tuple[Any, list[HookDecision]]:
    hooks = tuple(hooks)
    if not hooks:
        return result, []

    hook_request = build_hook_request(request=request, result=result)
    hook_result = build_hook_result(result)
    merged_result, decisions = run_success_hooks(
        hook_request,
        hook_result,
        hooks,
        plugin_failure_mode=plugin_failure_mode,
    )
    return merge_hook_result(result, merged_result), decisions


def build_hook_request(*, request: HandlerRequest, result: Any) -> HookRequest:
    metadata = dict(request.context.metadata)
    payload = request.payload if isinstance(request.payload, dict) else {}
    plugin_input = metadata.get("plugin")
    plugin_input = plugin_input if isinstance(plugin_input, dict) else {}

    prompt = _read_text(
        plugin_input.get("prompt"),
        payload.get("prompt"),
        metadata.get("prompt"),
    )
    reference_materials = _read_list(
        plugin_input.get("reference_materials"),
        payload.get("reference_materials"),
        metadata.get("reference_materials"),
    )
    action_risk = _read_enum(
        ActionRisk,
        plugin_input.get("action_risk"),
        payload.get("action_risk"),
        metadata.get("action_risk"),
        default=ActionRisk.LOW,
    )
    decision_type = _read_enum(
        DecisionType,
        plugin_input.get("decision_type"),
        payload.get("decision_type"),
        metadata.get("decision_type"),
        default=DecisionType.ANSWER,
    )

    return HookRequest(
        request_id=request.context.request_id,
        prompt=prompt,
        raw_output=_extract_result_output(result),
        reference_materials=reference_materials,
        action_risk=action_risk,
        decision_type=decision_type,
        metadata=metadata,
    )


def build_hook_result(result: Any) -> HookResult:
    if isinstance(result, HandlerResponse):
        return HookResult(
            ok=result.ok,
            output=result.data,
            meta=dict(result.meta),
        )
    if isinstance(result, dict):
        meta = result.get("meta")
        return HookResult(
            ok=True,
            output=result,
            meta=dict(meta) if isinstance(meta, dict) else {},
        )
    return HookResult(ok=True, output=result)


def merge_hook_result(result: Any, hook_result: HookResult) -> Any:
    if isinstance(result, HandlerResponse):
        return HandlerResponse(
            ok=result.ok,
            data=result.data,
            message=result.message,
            meta=dict(hook_result.meta),
        )
    if isinstance(result, dict):
        merged = dict(result)
        merged["meta"] = dict(hook_result.meta)
        return merged
    return result


def _merge_decision_into_result(
    result: HookResult,
    *,
    decision: HookDecision,
    hook_name: str,
) -> None:
    plugin_decisions = result.meta.get("plugin_decisions")
    if not isinstance(plugin_decisions, list):
        plugin_decisions = []
        result.meta["plugin_decisions"] = plugin_decisions

    plugin_decisions.append(_serialize_hook_decision(decision, hook_name=hook_name))

    if decision.credibility is not None:
        result.meta["credibility"] = _serialize_credibility(decision.credibility)
    result.meta["decision"] = decision.final_decision.value
    if decision.final_decision in {FinalDecision.BLOCK, FinalDecision.FALLBACK}:
        result.meta["high_priority_plugin_signal"] = decision.final_decision.value


def _serialize_hook_decision(
    decision: HookDecision,
    *,
    hook_name: str,
) -> dict[str, Any]:
    data = {
        "hook": hook_name,
        "final_decision": decision.final_decision.value,
        "should_raise": decision.should_raise,
        "fallback_payload": decision.fallback_payload,
        "mutate_output": decision.mutate_output,
        "output_override": decision.output_override,
        "plugin_meta": dict(decision.plugin_meta),
    }
    if decision.credibility is not None:
        data["credibility"] = _serialize_credibility(decision.credibility)
    return data


def _serialize_credibility(credibility: CredibilityResult) -> dict[str, Any]:
    data = asdict(credibility)
    data["confidence"] = float(data["confidence"])
    data["reasons"] = list(data["reasons"])
    return data


def _extract_result_output(result: Any) -> Any:
    if isinstance(result, HandlerResponse):
        return result.data
    return result


def _hook_name(hook: SuccessHook) -> str:
    return hook.__class__.__name__


def _normalize_plugin_failure_mode(plugin_failure_mode: str) -> str:
    normalized = plugin_failure_mode.strip().lower()
    if normalized not in {"fail_open", "fail_closed"}:
        raise ValueError(
            "plugin_failure_mode must be either 'fail_open' or 'fail_closed'."
        )
    return normalized


def _read_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str):
            return value
    return ""


def _read_list(*values: Any) -> list[Any]:
    for value in values:
        if isinstance(value, list):
            return list(value)
        if isinstance(value, tuple):
            return list(value)
    return []


def _read_enum(enum_type: type[ActionRisk] | type[DecisionType], *values: Any, default: Any):
    for value in values:
        if isinstance(value, enum_type):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in enum_type:
                if member.value == normalized:
                    return member
    return default
