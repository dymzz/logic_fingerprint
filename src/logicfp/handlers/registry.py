from __future__ import annotations

import importlib
from collections.abc import Callable

from ..handler_registry import HandlerRegistry
from .demo_handlers import register_demo_handlers

HandlerRegistrar = Callable[[HandlerRegistry], None]


def compose_handler_registrars(*registrars: HandlerRegistrar | None) -> HandlerRegistrar:
    active_registrars = [registrar for registrar in registrars if registrar is not None]

    def register_all(handler_registry: HandlerRegistry) -> None:
        for registrar in active_registrars:
            registrar(handler_registry)

    return register_all


def load_handler_registrar(spec: str) -> HandlerRegistrar:
    module_name, separator, attr_name = spec.partition(":")
    if not module_name:
        raise ValueError("Handler registrar spec must include a module path.")
    if not separator:
        attr_name = "register_handlers"

    module = importlib.import_module(module_name)
    registrar = getattr(module, attr_name, None)
    if registrar is None:
        raise AttributeError(
            f"Handler registrar '{attr_name}' was not found in module '{module_name}'.",
        )
    if not callable(registrar):
        raise TypeError(
            f"Handler registrar '{attr_name}' in module '{module_name}' is not callable.",
        )
    return registrar


def load_handler_registrars(specs: tuple[str, ...] | list[str]) -> HandlerRegistrar | None:
    if not specs:
        return None
    return compose_handler_registrars(*(load_handler_registrar(spec) for spec in specs))


def register_builtin_handlers(
    handler_registry: HandlerRegistry,
    *,
    include_demo: bool = False,
) -> None:
    if include_demo:
        register_demo_handlers(handler_registry)
