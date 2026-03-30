from __future__ import annotations

from typing import Any

__all__ = [
    "protect",
    "create_protector",
]


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
    config_file: str | None = None,
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
