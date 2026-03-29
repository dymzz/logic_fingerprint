from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from logicfp.domain.models import HandlerRequest
from logicfp.handler_registry import HandlerRegistry
from logicfp.handlers import load_handler_registrar, load_handler_registrars
from logicfp.runtime import build_production_runtime

def test_load_handler_registrar_supports_default_function_name(monkeypatch):
    module = types.ModuleType("tests.dynamic_handlers_default")

    def register_handlers(handler_registry: HandlerRegistry) -> None:
        handler_registry.register("default_loaded_handler", lambda request: {"ok": True})

    module.register_handlers = register_handlers
    monkeypatch.setitem(sys.modules, "tests.dynamic_handlers_default", module)

    registrar = load_handler_registrar("tests.dynamic_handlers_default")
    registry = HandlerRegistry()
    registrar(registry)

    assert registry.names() == ["default_loaded_handler"]


def test_load_handler_registrar_rejects_non_callable_attribute(monkeypatch):
    module = types.ModuleType("tests.dynamic_handlers_invalid")
    module.register_handlers = "not-callable"
    monkeypatch.setitem(sys.modules, "tests.dynamic_handlers_invalid", module)

    with pytest.raises(TypeError):
        load_handler_registrar("tests.dynamic_handlers_invalid")


def test_build_production_runtime_loads_registrars_from_settings(monkeypatch):
    first_module = types.ModuleType("tests.dynamic_handlers_one")
    second_module = types.ModuleType("tests.dynamic_handlers_two")

    def register_handlers(handler_registry: HandlerRegistry) -> None:
        handler_registry.register("loaded_one", lambda request: {"ok": True})

    def register_more_handlers(handler_registry: HandlerRegistry) -> None:
        handler_registry.register("loaded_two", lambda request: {"ok": True})

    first_module.register_handlers = register_handlers
    second_module.register_more_handlers = register_more_handlers
    monkeypatch.setitem(sys.modules, "tests.dynamic_handlers_one", first_module)
    monkeypatch.setitem(sys.modules, "tests.dynamic_handlers_two", second_module)

    runtime = build_production_runtime(
        handler_registrars=(
            "tests.dynamic_handlers_one",
            "tests.dynamic_handlers_two:register_more_handlers",
        ),
    )

    assert runtime.handler_registry.names() == ["loaded_one", "loaded_two"]


def test_load_handler_registrars_returns_none_for_empty_input():
    assert load_handler_registrars(()) is None


def test_build_production_runtime_loads_example_registrar(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    runtime = build_production_runtime(
        handler_registrars=("examples.production_handlers",),
    )

    assert runtime.handler_registry.names() == ["inventory_lookup", "order_quote"]


def test_build_production_runtime_loads_service_wired_example(monkeypatch, tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        """
example_services:
  base_stock: 31
  discount_rate: 0.20
  tax_rate: 0.05
  currency: USD
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)
    monkeypatch.delenv("EXAMPLE_BASE_STOCK", raising=False)
    monkeypatch.delenv("EXAMPLE_DISCOUNT_RATE", raising=False)
    monkeypatch.delenv("EXAMPLE_TAX_RATE", raising=False)
    monkeypatch.delenv("EXAMPLE_CURRENCY", raising=False)

    runtime = build_production_runtime(
        handler_registrars=("examples.production_services",),
    )

    inventory = runtime.middleware.execute_handler(
        "inventory_snapshot",
        request=HandlerRequest(payload={"sku": "SKU-9000", "warehouse": "east"}),
    )
    quote = asyncio.run(
        runtime.middleware.execute_handler_async(
            "order_quote_with_services",
            request=HandlerRequest(
                payload={"order_id": "ORDER-7", "items": [10, 20, 30]},
            ),
        )
    )

    assert runtime.handler_registry.names() == [
        "inventory_snapshot",
        "order_quote_with_services",
    ]
    assert inventory.succeeded is True
    assert inventory.result.data["quantity"] == 31
    assert quote.succeeded is True
    assert quote.result.data["currency"] == "USD"
    assert quote.result.data["discount"] == 12.0
    assert quote.result.data["tax"] == 2.4
    assert quote.result.data["total"] == 50.4
