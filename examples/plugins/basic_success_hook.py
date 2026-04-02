from __future__ import annotations

from logicfp import create_protector
from logicfp.domain.models import HandlerRequest
from logicfp.plugins import (
    CredibilityResult,
    FinalDecision,
    HookDecision,
    SuccessHook,
)
from logicfp.runtime import build_demo_runtime


class BasicCredibilityHook(SuccessHook):
    def after_success(self, request, result):
        prompt = request.prompt.strip()
        reasons: list[str] = []
        confidence = 0.7

        if not prompt:
            confidence = 0.35
            reasons.append("prompt is empty")
        if not request.reference_materials:
            confidence -= 0.15
            reasons.append("reference_materials is empty")

        confidence = max(0.0, min(1.0, confidence))
        verdict = "warn" if confidence < 0.6 else "allow"
        decision = FinalDecision.WARN if verdict == "warn" else FinalDecision.ALLOW

        return HookDecision(
            credibility=CredibilityResult(
                confidence=confidence,
                risk_level="medium" if verdict == "warn" else "low",
                verdict=verdict,
                reasons=reasons or ["basic local checks passed"],
            ),
            final_decision=decision,
            plugin_meta={"plugin": "basic_credibility"},
        )


def build_runtime_with_plugin():
    return build_demo_runtime(success_hooks=[BasicCredibilityHook()])


def build_protector_with_plugin():
    return create_protector(
        advanced={"success_hooks": [BasicCredibilityHook()]},
    )


if __name__ == "__main__":
    protector = build_protector_with_plugin()

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        return {"content": "local plugin demo"}

    response = guarded(
        payload={
            "prompt": "summarize this report",
            "reference_materials": ["report.md"],
            "action_risk": "low",
            "decision_type": "answer",
        }
    )
    print(response)
