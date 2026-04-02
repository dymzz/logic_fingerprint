from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


SUPPORTED_HOOK_CONTRACT_VERSION = "1.0.0"


class ActionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DecisionType(str, Enum):
    ANSWER = "answer"
    ACTION = "action"


class FinalDecision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    FALLBACK = "fallback"
    BLOCK = "block"


@dataclass(slots=True)
class HookRequest:
    request_id: str | None = None
    prompt: str = ""
    raw_output: Any = None
    reference_materials: list[Any] = field(default_factory=list)
    action_risk: ActionRisk = ActionRisk.LOW
    decision_type: DecisionType = DecisionType.ANSWER
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class HookResult:
    ok: bool
    output: Any = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CredibilityResult:
    confidence: float
    risk_level: str
    verdict: str
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HookDecision:
    credibility: CredibilityResult | None = None
    final_decision: FinalDecision = FinalDecision.ALLOW
    should_raise: bool = False
    fallback_payload: Any = None
    mutate_output: bool = False
    output_override: Any = None
    plugin_meta: dict[str, Any] = field(default_factory=dict)


class SuccessHook(Protocol):
    def after_success(
        self,
        request: HookRequest,
        result: HookResult,
    ) -> HookDecision | None:
        ...
