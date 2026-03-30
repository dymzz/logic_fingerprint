from __future__ import annotations

from pathlib import Path
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


def protect(
    *,
    input_model: type[Any] | None = None,
    output_model: type[Any] | None = None,
    simple: bool = True,
):
    from .decorator import protect as _protect

    return _protect(
        input_model=input_model,
        output_model=output_model,
        simple=simple,
    )


def create_protector(
    *,
    config_file: str | Path | None = None,
    probe_rate: float | None = None,
    probe_interval_seconds: float | None = None,
    consecutive_success_threshold: int | None = None,
    total_nodes: int | None = None,
    global_fail_threshold: float | None = None,
    default_source: str | None = None,
    backend_type: str | None = None,
    event_logger: Any | None = None,
    advanced: dict[str, Any] | None = None,
    **advanced_kwargs: Any,
):
    from .decorator import create_protector as _create_protector

    return _create_protector(
        config_file=config_file,
        probe_rate=probe_rate,
        probe_interval_seconds=probe_interval_seconds,
        consecutive_success_threshold=consecutive_success_threshold,
        total_nodes=total_nodes,
        global_fail_threshold=global_fail_threshold,
        default_source=default_source,
        backend_type=backend_type,
        event_logger=event_logger,
        advanced=advanced,
        **advanced_kwargs,
    )


def __getattr__(name: str):
    if name in _ENGINEERING_EXPORTS:
        raise AttributeError(
            f"'logicfp.{name}' is not exported from the package root. "
            "Import it from 'logicfp.engineering' instead."
        )
    raise AttributeError(f"module 'logicfp' has no attribute '{name}'")
