from __future__ import annotations

from typing import Any, TypedDict, cast


class ErrorFactData(TypedDict):
    stage: str
    source: str
    recoverability: str
    code: str
    message: str
    details: dict[str, Any]


class ErrorPolicyData(TypedDict):
    action: str
    details: dict[str, Any]


class ErrorDetailsData(TypedDict, total=False):
    error_fact: ErrorFactData
    error_policy: ErrorPolicyData
    ai_error: dict[str, Any]
    errors: list[Any]


def get_error_details(error_like: Any) -> ErrorDetailsData:
    details = _resolve_error_details(error_like)
    return cast(ErrorDetailsData, dict(details) if isinstance(details, dict) else {})


def get_error_fact(error_like: Any) -> ErrorFactData | None:
    details = _resolve_error_details(error_like)
    fact = details.get("error_fact") if isinstance(details, dict) else None
    return cast(ErrorFactData | None, dict(fact) if isinstance(fact, dict) else None)


def get_error_policy(error_like: Any) -> ErrorPolicyData | None:
    details = _resolve_error_details(error_like)
    policy = details.get("error_policy") if isinstance(details, dict) else None
    return cast(ErrorPolicyData | None, dict(policy) if isinstance(policy, dict) else None)


def get_error_action(error_like: Any) -> str | None:
    policy = get_error_policy(error_like)
    if not isinstance(policy, dict):
        return None
    action = policy.get("action")
    return action if isinstance(action, str) else None


def _resolve_error_details(error_like: Any) -> dict[str, Any]:
    if isinstance(error_like, dict):
        details = error_like.get("details")
        if isinstance(details, dict):
            return details
        error = error_like.get("error")
        if isinstance(error, dict):
            nested_details = error.get("details")
            if isinstance(nested_details, dict):
                return nested_details
    details = getattr(error_like, "details", None)
    if isinstance(details, dict):
        return details
    return {}
