from __future__ import annotations

from typing import Any

__all__ = [
    "assemble_runtime",
    "build_demo_runtime",
    "build_production_runtime",
    "build_runtime",
    "create_http_app",
    "create_app",
    "create_demo_app",
]


def assemble_runtime(*args: Any, **kwargs: Any):
    from .runtime import assemble_runtime as _assemble_runtime

    return _assemble_runtime(*args, **kwargs)


def build_demo_runtime(*args: Any, **kwargs: Any):
    from .runtime import build_demo_runtime as _build_demo_runtime

    return _build_demo_runtime(*args, **kwargs)


def build_production_runtime(*args: Any, **kwargs: Any):
    from .runtime import build_production_runtime as _build_production_runtime

    return _build_production_runtime(*args, **kwargs)


def build_runtime(*args: Any, **kwargs: Any):
    from .runtime import build_runtime as _build_runtime

    return _build_runtime(*args, **kwargs)


def create_http_app(*args: Any, **kwargs: Any):
    from .app_factory import create_http_app as _create_http_app

    return _create_http_app(*args, **kwargs)


def create_app(*args: Any, **kwargs: Any):
    from .app_factory import create_app as _create_app

    return _create_app(*args, **kwargs)


def create_demo_app(*args: Any, **kwargs: Any):
    from .app_factory import create_demo_app as _create_demo_app

    return _create_demo_app(*args, **kwargs)
