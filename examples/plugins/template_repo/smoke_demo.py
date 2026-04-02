from __future__ import annotations

from logicfp import create_protector
from logicfp.domain.models import HandlerRequest

from logicfp_credibility_plugin import BasicCredibilityPlugin


def main() -> None:
    protector = create_protector(
        advanced={"success_hooks": [BasicCredibilityPlugin()]},
    )

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        return {"content": "template smoke demo"}

    result = guarded(
        payload={
            "prompt": "summarize this contract",
            "reference_materials": ["contract.md"],
            "action_risk": "low",
            "decision_type": "answer",
        }
    )
    print(result)


if __name__ == "__main__":
    main()
