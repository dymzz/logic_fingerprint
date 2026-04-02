from __future__ import annotations

from logicfp.plugins import (
    CredibilityResult,
    FinalDecision,
    HookDecision,
    SUPPORTED_HOOK_CONTRACT_VERSION,
    SuccessHook,
)


PLUGIN_NAME = "logicfp-credibility-plugin-template"
SUPPORTED_LOGICFP_HOOK_CONTRACT = SUPPORTED_HOOK_CONTRACT_VERSION


class BasicCredibilityPlugin(SuccessHook):
    def after_success(self, request, result):
        prompt = request.prompt.strip()
        references = request.reference_materials

        confidence = 0.75
        reasons: list[str] = []

        if not prompt:
            confidence = 0.4
            reasons.append("prompt is empty")
        if not references:
            confidence -= 0.2
            reasons.append("reference_materials is empty")

        confidence = max(0.0, min(1.0, confidence))
        final_decision = FinalDecision.WARN if confidence < 0.6 else FinalDecision.ALLOW

        return HookDecision(
            credibility=CredibilityResult(
                confidence=confidence,
                risk_level="medium" if final_decision is FinalDecision.WARN else "low",
                verdict=final_decision.value,
                reasons=reasons or ["template checks passed"],
            ),
            final_decision=final_decision,
            plugin_meta={
                "plugin_name": PLUGIN_NAME,
                "hook_contract": SUPPORTED_LOGICFP_HOOK_CONTRACT,
            },
        )
