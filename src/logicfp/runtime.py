from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .application.context_builder import ContextBuilder
from .application.metrics import InMemoryMetrics
from .config import RuntimeConfig, RuntimeSettings, build_runtime_config, build_runtime_settings
from .domain.executor import LogicFingerprintExecutor
from .domain.fsm import LogicFingerprintFSM
from .handler_registry import HandlerRegistry
from .handlers import (
    compose_handler_registrars,
    load_handler_registrars,
    register_builtin_handlers,
)
from .infra.consensus import HeartbeatService, build_consensus_backend
from .middleware import LogicFingerprintMiddleware

@dataclass(slots=True)
class LogicFingerprintRuntime:
    config: RuntimeConfig
    settings: RuntimeSettings
    backend: object
    fsm: object
    executor: object
    metrics: object
    handler_registry: object
    middleware: object
    heartbeat: object
    context_builder: object

    @property
    def instance_id(self) -> str:
        return self.settings.instance_id

    @property
    def default_source(self) -> str:
        return self.settings.default_source

def assemble_runtime(
    *,
    config: RuntimeConfig,
    settings: RuntimeSettings,
    backend: object,
    handler_registry: HandlerRegistry | None = None,
    metrics: InMemoryMetrics | None = None,
    context_builder: ContextBuilder | None = None,
    register_handlers: Callable[[HandlerRegistry], None] | None = None,
) -> LogicFingerprintRuntime:
    fsm = LogicFingerprintFSM(
        instance_id=settings.instance_id,
        config=config,
        backend=backend,
    )
    executor = LogicFingerprintExecutor(fsm)
    metrics = metrics or InMemoryMetrics()
    handler_registry = handler_registry or HandlerRegistry()
    heartbeat = HeartbeatService(backend=backend, instance_id=settings.instance_id)
    context_builder = context_builder or ContextBuilder(
        default_source=settings.default_source,
    )
    middleware = LogicFingerprintMiddleware(
        executor=executor,
        handler_registry=handler_registry,
        metrics=metrics,
        context_builder=context_builder,
    )
    if register_handlers is not None:
        register_handlers(handler_registry)

    return LogicFingerprintRuntime(
        config=config,
        settings=settings,
        backend=backend,
        fsm=fsm,
        executor=executor,
        metrics=metrics,
        handler_registry=handler_registry,
        middleware=middleware,
        heartbeat=heartbeat,
        context_builder=context_builder,
    )


def build_demo_runtime(
    *,
    config: RuntimeConfig | None = None,
    settings: RuntimeSettings | None = None,
    backend: object | None = None,
    redis_client: object | None = None,
    instance_id: str | None = None,
    default_source: str | None = None,
    backend_type: str | None = None,
    handler_registrars: tuple[str, ...] | None = None,
    redis_url: str | None = None,
    redis_decode_responses: bool | None = None,
    redis_key: str | None = None,
    redis_key_prefix: str | None = None,
    redis_ttl_seconds: int | None = None,
    config_file: str | Path | None = None,
    register_handlers: Callable[[HandlerRegistry], None] | None = None,
) -> LogicFingerprintRuntime:
    config = config or build_runtime_config(config_file=config_file)
    settings = settings or build_runtime_settings(
        instance_id=instance_id,
        default_source=default_source,
        backend_type=backend_type,
        handler_registrars=handler_registrars,
        redis_url=redis_url,
        redis_decode_responses=redis_decode_responses,
        redis_key=redis_key,
        redis_key_prefix=redis_key_prefix,
        redis_ttl_seconds=redis_ttl_seconds,
        config_file=config_file,
    )
    backend = backend or build_consensus_backend(
        settings=settings,
        redis_client=redis_client,
    )
    return assemble_runtime(
        config=config,
        settings=settings,
        backend=backend,
        register_handlers=compose_handler_registrars(
            lambda handler_registry: register_builtin_handlers(
                handler_registry,
                include_demo=True,
            ),
            load_handler_registrars(settings.handler_registrars),
            register_handlers,
        ),
    )


def build_production_runtime(
    *,
    config: RuntimeConfig | None = None,
    settings: RuntimeSettings | None = None,
    backend: object | None = None,
    redis_client: object | None = None,
    instance_id: str | None = None,
    default_source: str | None = None,
    backend_type: str | None = None,
    handler_registrars: tuple[str, ...] | None = None,
    redis_url: str | None = None,
    redis_decode_responses: bool | None = None,
    redis_key: str | None = None,
    redis_key_prefix: str | None = None,
    redis_ttl_seconds: int | None = None,
    config_file: str | Path | None = None,
    register_handlers: Callable[[HandlerRegistry], None] | None = None,
) -> LogicFingerprintRuntime:
    config = config or build_runtime_config(config_file=config_file)
    settings = settings or build_runtime_settings(
        instance_id=instance_id,
        default_source=default_source,
        backend_type=backend_type,
        handler_registrars=handler_registrars,
        redis_url=redis_url,
        redis_decode_responses=redis_decode_responses,
        redis_key=redis_key,
        redis_key_prefix=redis_key_prefix,
        redis_ttl_seconds=redis_ttl_seconds,
        config_file=config_file,
    )
    backend = backend or build_consensus_backend(
        settings=settings,
        redis_client=redis_client,
    )
    return assemble_runtime(
        config=config,
        settings=settings,
        backend=backend,
        register_handlers=compose_handler_registrars(
            register_builtin_handlers,
            load_handler_registrars(settings.handler_registrars),
            register_handlers,
        ),
    )


def build_runtime(**kwargs: object) -> LogicFingerprintRuntime:
    return build_demo_runtime(**kwargs)

