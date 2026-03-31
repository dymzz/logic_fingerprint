import pytest

pytest.importorskip("pydantic")
from logicfp.application.context_builder import ContextBuilder
from logicfp.config import RuntimeConfig, build_runtime_settings
from logicfp.handler_registry import HandlerRegistry
from logicfp.handlers import (
    compose_handler_registrars,
    register_builtin_handlers,
)
from logicfp.infra.consensus import InMemoryConsensusBackend
from logicfp.runtime import (
    assemble_runtime,
    build_demo_runtime,
    build_production_runtime,
    build_runtime,
)


def test_assemble_runtime_supports_custom_registration():
    registry = HandlerRegistry()

    def register_handlers(handler_registry: HandlerRegistry) -> None:
        handler_registry.register("custom_handler", lambda request: {"ok": True})

    runtime = assemble_runtime(
        config=RuntimeConfig(),
        settings=build_runtime_settings(
            instance_id="custom-node",
            default_source="custom",
        ),
        backend=InMemoryConsensusBackend(),
        handler_registry=registry,
        context_builder=ContextBuilder(default_source="custom"),
        register_handlers=register_handlers,
    )

    assert runtime.instance_id == "custom-node"
    assert runtime.context_builder.default_source == "custom"
    assert runtime.handler_registry is registry
    assert "custom_handler" in runtime.handler_registry.names()


def test_runtime_contains_registered_handlers():
    runtime = build_runtime()
    names = runtime.handler_registry.names()
    assert "echo_payload" in names
    assert "sum_numbers" in names
    assert "async_echo_payload" in names


def test_build_demo_runtime_keeps_default_demo_handlers():
    runtime = build_demo_runtime()

    assert runtime.instance_id == "node-a"
    assert runtime.config.probe_rate == 0.2
    assert "demo_timeout" in runtime.handler_registry.names()


def test_build_production_runtime_has_no_demo_handlers():
    runtime = build_production_runtime()

    assert runtime.instance_id == "node-a"
    assert runtime.handler_registry.names() == []


def test_register_builtin_handlers_is_empty_without_demo():
    registry = HandlerRegistry()

    register_builtin_handlers(registry)

    assert registry.names() == []


def test_build_production_runtime_accepts_custom_handler_registrar():
    def register_handlers(handler_registry: HandlerRegistry) -> None:
        handler_registry.register("production_handler", lambda request: {"ok": True})

    runtime = build_production_runtime(register_handlers=register_handlers)

    assert runtime.handler_registry.names() == ["production_handler"]


def test_build_demo_runtime_composes_builtin_and_custom_handlers():
    def register_handlers(handler_registry: HandlerRegistry) -> None:
        handler_registry.register("custom_demo_handler", lambda request: {"ok": True})

    runtime = build_demo_runtime(register_handlers=register_handlers)

    assert "sum_numbers" in runtime.handler_registry.names()
    assert "custom_demo_handler" in runtime.handler_registry.names()


def test_compose_handler_registrars_runs_in_order():
    registry = HandlerRegistry()
    calls: list[str] = []

    def register_first(handler_registry: HandlerRegistry) -> None:
        calls.append("first")
        handler_registry.register("first_handler", lambda request: {"ok": True})

    def register_second(handler_registry: HandlerRegistry) -> None:
        calls.append("second")
        handler_registry.register("second_handler", lambda request: {"ok": True})

    compose_handler_registrars(register_first, register_second)(registry)

    assert calls == ["first", "second"]
    assert registry.names() == ["first_handler", "second_handler"]
