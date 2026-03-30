from __future__ import annotations

from logicfp import create_protector
from logicfp.domain.models import HandlerRequest
from logicfp.user_mode import build_ai_error_recognition, get_error_details


class VendorGatewayTimeout(RuntimeError):
    def __init__(self, provider: str, model: str) -> None:
        super().__init__(f"{provider} gateway timed out while calling {model}")
        self.provider = provider
        self.model = model


def recognize_vendor_gateway_error(context):
    if context.class_name_lower != "vendorgatewaytimeout":
        return None
    provider = getattr(context.exc, "provider", None) or context.provider or "vendor-gateway"
    model = getattr(context.exc, "model", None) or context.model
    details = dict(context.base_details)
    details["gateway"] = "vendor-router"
    return build_ai_error_recognition(
        "UPSTREAM_OVERLOADED",
        provider=provider,
        model=model,
        matched_signals=("local_vendor_gateway_recognizer",),
        details=details,
    )


gateway_protector = create_protector(
    default_source="vendor_gateway",
    advanced={
        "ai_error_recognizers": [recognize_vendor_gateway_error],
    },
)
fallback_gateway_protector = create_protector(
    default_source="vendor_gateway",
    advanced={
        "ai_error_recognizers": [recognize_vendor_gateway_error],
    },
)


@gateway_protector.protect(simple=False)
def fetch_model_summary(request: HandlerRequest) -> dict[str, object]:
    raise VendorGatewayTimeout(provider="openai", model="gpt-5-mini")


@fallback_gateway_protector.protect(simple=False)
def fetch_model_summary_for_fallback(request: HandlerRequest) -> dict[str, object]:
    raise VendorGatewayTimeout(provider="openai", model="gpt-5-mini")


def fetch_model_summary_with_fallback(payload: dict[str, object]) -> dict[str, object]:
    result = fetch_model_summary_for_fallback(payload=payload)
    if result["ok"]:
        return result["result"]
    details = get_error_details(result)
    ai_error = details.get("ai_error") if isinstance(details, dict) else None
    if isinstance(ai_error, dict) and ai_error.get("code") == "UPSTREAM_OVERLOADED":
        return {
            "source": "local-cache",
            "summary": "cached summary placeholder",
            "stale": True,
        }
    return {
        "source": "error",
        "error": result["error"],
    }


def main() -> None:
    result = fetch_model_summary(payload={"topic": "release-notes"})
    print(result)
    print(fetch_model_summary_with_fallback({"topic": "release-notes"}))


if __name__ == "__main__":
    main()
