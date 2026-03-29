from __future__ import annotations

from typing import Any

from ._version import __version__

__all__ = [
    "protect",
    "create_protector",
]

_ENGINEERING_EXPORTS = {
    "assemble_runtime",
    "build_demo_runtime",
    "build_production_runtime",
    "build_runtime",
    "create_http_app",
    "create_app",
    "create_demo_app",
}


def protect(*args: Any, **kwargs: Any):
    from .decorator import protect as _protect

    return _protect(*args, **kwargs)


def create_protector(*args: Any, **kwargs: Any):
    from .decorator import create_protector as _create_protector

    return _create_protector(*args, **kwargs)


def __getattr__(name: str):
    if name in _ENGINEERING_EXPORTS:
        raise AttributeError(
            f"'logicfp.{name}' is not exported from the package root. "
            "Import it from 'logicfp.engineering' instead."
        )
    raise AttributeError(f"module 'logicfp' has no attribute '{name}'")
