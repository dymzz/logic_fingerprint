from __future__ import annotations

from logicfp import create_protector
from logicfp.domain.models import HandlerRequest
from logicfp.user_mode import get_error_action


class CatalogBackendError(Exception):
    pass


def resolve_action(payload: dict[str, object]) -> dict[str, object] | None:
    fact = payload.get("fact")
    if not isinstance(fact, dict):
        return None
    if fact.get("source") == "unknown" and fact.get("recoverability") == "unknown":
        return {
            "action": "fallback",
            "user_effect": "soft_notice",
            "observability": "aggregate",
            "details": {
                "reason": "local catalog fallback is allowed for unknown backend failures",
            },
        }
    return None


def _build_inventory_protector():
    return create_protector(
        default_source="inventory_tool",
        advanced={"error_action_resolver": resolve_action},
    )


inventory_protector = _build_inventory_protector()
fallback_inventory_protector = _build_inventory_protector()


@inventory_protector.protect(simple=False)
def fetch_inventory_snapshot(request: HandlerRequest) -> dict[str, object]:
    raise CatalogBackendError("catalog backend did not return a usable response")


@fallback_inventory_protector.protect(simple=False)
def fetch_inventory_snapshot_for_fallback(request: HandlerRequest) -> dict[str, object]:
    raise CatalogBackendError("catalog backend did not return a usable response")


def fetch_inventory_with_fallback(payload: dict[str, object]) -> dict[str, object]:
    result = fetch_inventory_snapshot_for_fallback(payload=payload)
    if result["ok"]:
        return result["result"]

    if get_error_action(result) == "fallback":
        return {
            "source": "local-fallback",
            "items": [],
            "stale": True,
        }

    return {
        "source": "error",
        "error": result["error"],
    }


def main() -> None:
    result = fetch_inventory_snapshot(payload={"warehouse": "cn-east-1"})
    print(result)
    print(fetch_inventory_with_fallback({"warehouse": "cn-east-1"}))


if __name__ == "__main__":
    main()
