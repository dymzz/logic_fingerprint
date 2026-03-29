"""Built-in handler registrations."""

from .demo_handlers import register_demo_handlers
from .registry import (
    HandlerRegistrar,
    compose_handler_registrars,
    load_handler_registrar,
    load_handler_registrars,
    register_builtin_handlers,
)
from .schemas import SumNumbersInput, SumNumbersOutput

__all__ = [
    "HandlerRegistrar",
    "compose_handler_registrars",
    "load_handler_registrar",
    "load_handler_registrars",
    "register_builtin_handlers",
    "register_demo_handlers",
    "SumNumbersInput",
    "SumNumbersOutput",
]
