from __future__ import annotations

from typing import Any

__all__ = ["build_runtime", "protect", "create_protector"]


def build_runtime(*args: Any, **kwargs: Any):
    from .runtime import build_runtime as _build_runtime

    return _build_runtime(*args, **kwargs)


def protect(*args: Any, **kwargs: Any):
    from .protect import protect as _protect

    return _protect(*args, **kwargs)


def create_protector(*args: Any, **kwargs: Any):
    from .protect import create_protector as _create_protector

    return _create_protector(*args, **kwargs)
