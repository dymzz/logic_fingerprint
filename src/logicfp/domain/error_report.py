from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, NotRequired, Required, TypedDict


class ErrorActionResolverPayload(TypedDict):
    fact: dict[str, Any]
    default_action: dict[str, Any]
    default_policy: dict[str, Any]


class ErrorActionResolverResult(TypedDict, total=False):
    action: Required[str]
    user_effect: NotRequired[str]
    observability: NotRequired[str]
    details: NotRequired[dict[str, Any]]


ErrorActionResolver = Callable[[ErrorActionResolverPayload], ErrorActionResolverResult | None]
ErrorPolicyResolver = ErrorActionResolver


@dataclass(frozen=True)
class ErrorFact:
    stage: str
    source: str
    recoverability: str
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "source": self.source,
            "recoverability": self.recoverability,
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ErrorPolicy:
    action: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ErrorReport:
    fact: ErrorFact
    policy: ErrorPolicy

    def as_dict(self) -> dict[str, Any]:
        return {
            "fact": self.fact.as_dict(),
            "policy": self.policy.as_dict(),
        }


def build_error_report(
    *,
    code: str,
    message: str,
    stage_hint: str | None = None,
    details: dict[str, Any] | None = None,
    action_resolver: ErrorActionResolver | None = None,
) -> ErrorReport:
    safe_details = dict(details or {})
    ai_error = safe_details.get("ai_error")
    certainty = _resolve_certainty(ai_error)
    recoverability = _resolve_recoverability(code, ai_error)
    impact = _resolve_impact(code, ai_error)
    fact_details = _summarize_fact_details(safe_details)
    fact_details["certainty"] = certainty
    fact_details["impact"] = impact
    fact = ErrorFact(
        stage=_resolve_stage(code, stage_hint, ai_error),
        source=_resolve_source(code, ai_error),
        recoverability=recoverability,
        code=code,
        message=message,
        details=fact_details,
    )
    policy = _resolve_default_policy(fact)
    if action_resolver is not None and _should_resolve_policy_by_hook(fact):
        resolved = _resolve_policy_by_hook(action_resolver, fact, policy)
        if resolved is not None:
            policy = resolved
    return ErrorReport(fact=fact, policy=policy)


def _resolve_stage(code: str, stage_hint: str | None, ai_error: dict[str, Any] | None) -> str:
    if stage_hint in {"input", "output", "plugin"}:
        return stage_hint
    ai_code = _ai_code(ai_error)
    if ai_code in {"INPUT_INVALID", "CONTEXT_TOO_LONG"}:
        return "input"
    if ai_code in {"OUTPUT_PARSE_ERROR", "OUTPUT_SCHEMA_INVALID", "OUTPUT_TRUNCATED", "EMPTY_RESULT"}:
        return "output"
    if ai_code is not None:
        return "dependency"
    if stage_hint == "execute":
        return "execute"
    if code in {"ERR_VALIDATION", "ERR_NORM"}:
        return "input"
    if code in {"ERR_OUTPUT_VALIDATION", "ERR_NULL"}:
        return "output"
    if code == "ERR_EXECUTION_BLOCKED":
        return "execute"
    return "execute"


def _resolve_source(code: str, ai_error: dict[str, Any] | None) -> str:
    ai_code = _ai_code(ai_error)
    if ai_code in {"NET_CONNECT", "NET_TIMEOUT"}:
        return "environment"
    if ai_code in {"AUTH_INVALID", "AUTH_FORBIDDEN", "MODEL_NOT_FOUND", "QUOTA_EXHAUSTED"}:
        return "environment"
    if ai_code in {
        "STREAM_BROKEN",
        "RATE_LIMIT_REQUEST",
        "RATE_LIMIT_TOKEN",
        "UPSTREAM_OVERLOADED",
        "UPSTREAM_5XX",
        "SAFETY_REFUSAL",
        "TOOL_TIMEOUT",
        "TOOL_EXEC_ERROR",
        "TOOL_NOT_FOUND",
        "TOOL_ARGS_INVALID",
    }:
        return "dependency"
    if ai_code in {"INPUT_INVALID", "CONTEXT_TOO_LONG"}:
        return "caller"
    if ai_code in {"OUTPUT_PARSE_ERROR", "OUTPUT_SCHEMA_INVALID", "OUTPUT_TRUNCATED", "EMPTY_RESULT"}:
        return "dependency"
    if code in {"ERR_VALIDATION", "ERR_NORM"}:
        return "caller"
    if code in {"ERR_OUTPUT_VALIDATION", "ERR_NULL", "ERR_LOGIC"}:
        return "system"
    if code == "ERR_TIMEOUT":
        return "dependency"
    if code == "ERR_EXECUTION_BLOCKED":
        return "system"
    return "unknown"


def _resolve_certainty(ai_error: dict[str, Any] | None) -> str:
    if ai_error is None:
        return "deterministic"
    matched_signals = ai_error.get("matched_signals")
    if isinstance(matched_signals, list) and "model_classifier" in matched_signals:
        return "heuristic"
    return "deterministic"


def _resolve_recoverability(code: str, ai_error: dict[str, Any] | None) -> str:
    if ai_error is not None:
        retryable = ai_error.get("retryable")
        ai_code = _ai_code(ai_error)
        if retryable is True:
            return "retryable"
        if ai_code in {"OUTPUT_PARSE_ERROR", "OUTPUT_SCHEMA_INVALID", "OUTPUT_TRUNCATED", "EMPTY_RESULT"}:
            return "degradable"
        if retryable is False:
            return "non_recoverable"
        return "unknown"
    if code == "ERR_TIMEOUT":
        return "retryable"
    if code in {"ERR_VALIDATION", "ERR_NORM", "ERR_LOGIC", "ERR_OUTPUT_VALIDATION", "ERR_NULL"}:
        return "non_recoverable" if code != "ERR_OUTPUT_VALIDATION" else "degradable"
    if code == "ERR_EXECUTION_BLOCKED":
        return "non_recoverable"
    return "unknown"


def _resolve_impact(code: str, ai_error: dict[str, Any] | None) -> str:
    recoverability = _resolve_recoverability(code, ai_error)
    if recoverability == "retryable":
        return "major"
    if recoverability == "degradable":
        return "major"
    if code == "ERR_EXECUTION_BLOCKED":
        return "fatal"
    if ai_error is not None and _ai_code(ai_error) == "CLIENT_CANCELLED":
        return "minor"
    return "fatal"



def _summarize_fact_details(details: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if "errors" in details:
        errors = details["errors"]
        if isinstance(errors, list):
            summary["error_count"] = len(errors)
    ai_error = details.get("ai_error")
    if isinstance(ai_error, dict):
        summary["ai_error_code"] = ai_error.get("code")
        summary["provider"] = ai_error.get("provider")
        summary["phase"] = ai_error.get("phase")
        ai_details = ai_error.get("details")
        if isinstance(ai_details, dict):
            for key in ("http_status", "provider_code", "tool_name", "schema_name"):
                value = ai_details.get(key)
                if value is not None:
                    summary[key] = value
    return summary


def _resolve_default_policy(fact: ErrorFact) -> ErrorPolicy:
    recoverability = fact.recoverability
    impact = _derived_impact_from_details(fact.details) or _resolve_impact(fact.code, {})

    if fact.code == "ERR_EXECUTION_BLOCKED":
        return ErrorPolicy(action="trip", details={"user_effect": "hard_error", "observability": "aggregate"})
    if recoverability == "retryable":
        return ErrorPolicy(action="retry", details={"user_effect": "soft_notice", "observability": "aggregate"})
    if recoverability == "degradable":
        return ErrorPolicy(action="fallback", details={"user_effect": "soft_notice", "observability": "aggregate"})
    if impact == "minor":
        return ErrorPolicy(action="warn", details={"user_effect": "transparent", "observability": "sample"})
    if fact.source == "system":
        return ErrorPolicy(action="block", details={"user_effect": "hard_error", "observability": "alert"})
    if fact.source in {"caller", "environment", "dependency"}:
        return ErrorPolicy(action="block", details={"user_effect": "hard_error", "observability": "aggregate"})
    return ErrorPolicy(action="warn", details={"user_effect": "soft_notice", "observability": "aggregate"})


def _should_resolve_policy_by_hook(fact: ErrorFact) -> bool:
    certainty = _derived_certainty_from_details(fact.details)
    return certainty == "heuristic" or fact.recoverability == "unknown" or fact.source == "unknown"


def _resolve_policy_by_hook(
    action_resolver: ErrorActionResolver,
    fact: ErrorFact,
    default_policy: ErrorPolicy,
) -> ErrorPolicy | None:
    try:
        result = action_resolver(_build_action_resolver_payload(fact, default_policy))
    except Exception:
        return None
    return _normalize_policy(result, default_policy)


def _normalize_policy(result: Any, default_policy: ErrorPolicy) -> ErrorPolicy | None:
    if isinstance(result, ErrorPolicy):
        return result
    if not isinstance(result, dict):
        return None
    action = _coerce_text(result.get("action")) or _coerce_text(result.get("disposition")) or default_policy.action
    merged_details = dict(default_policy.details)
    user_effect = _coerce_text(result.get("user_effect"))
    observability = _coerce_text(result.get("observability"))
    if user_effect is not None:
        merged_details["user_effect"] = user_effect
    if observability is not None:
        merged_details["observability"] = observability
    extra_details = result.get("details")
    if isinstance(extra_details, dict):
        merged_details.update(extra_details)
    return ErrorPolicy(action=action, details=merged_details)


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _ai_code(ai_error: dict[str, Any] | None) -> str | None:
    if not isinstance(ai_error, dict):
        return None
    value = ai_error.get("code")
    return value if isinstance(value, str) else None


def _build_action_resolver_payload(
    fact: ErrorFact,
    default_policy: ErrorPolicy,
) -> ErrorActionResolverPayload:
    payload: ErrorActionResolverPayload = {
        "fact": fact.as_dict(),
        "default_action": default_policy.as_dict(),
        # Legacy compatibility key. New code should prefer default_action.
        "default_policy": default_policy.as_dict(),
    }
    return payload



def _derived_certainty_from_details(details: dict[str, Any]) -> str | None:
    value = details.get("certainty")
    return value if isinstance(value, str) else None


def _derived_impact_from_details(details: dict[str, Any]) -> str | None:
    value = details.get("impact")
    return value if isinstance(value, str) else None

