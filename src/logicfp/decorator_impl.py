from __future__ import annotations

from dataclasses import asdict, is_dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar
import inspect
import sys

from pydantic import BaseModel

from .application.context_builder import ContextBuilder
from .application.metrics import InMemoryMetrics
from .application.validator import validate_input, validate_output
from .config import (
    DECORATOR_PROFILE,
    RuntimeConfig,
    RuntimeSettings,
    build_runtime_config,
    build_runtime_settings,
)
from .domain.executor import LogicFingerprintExecutor
from .domain.fsm import LogicFingerprintFSM
from .domain.models import HandlerRequest, RequestContext
from .infra.consensus import build_consensus_backend
from .infra.logging import EventLogger, LogEvent, NullEventLogger

F = TypeVar("F", bound=Callable[..., Any])


class ProtectRuntimeError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.context = context or {}
        

class Protector:
    def __init__(
        self,
        *,
        instance_id: str | None = None,
        probe_rate: float | None = None,
        probe_interval_seconds: float | None = None,
        consecutive_success_threshold: int | None = None,
        total_nodes: int | None = None,
        global_fail_threshold: float | None = None,
        default_source: str | None = None,
        backend_type: str | None = None,
        redis_url: str | None = None,
        redis_decode_responses: bool | None = None,
        redis_key: str | None = None,
        redis_key_prefix: str | None = None,
        redis_ttl_seconds: int | None = None,
        config_file: str | Path | None = None,
        config: RuntimeConfig | None = None,
        settings: RuntimeSettings | None = None,
        backend: object | None = None,
        redis_client: object | None = None,
        event_logger: EventLogger | None = None,
    ) -> None:
        config = config or build_runtime_config(
            probe_rate=probe_rate,
            probe_interval_seconds=probe_interval_seconds,
            consecutive_success_threshold=consecutive_success_threshold,
            total_nodes=total_nodes,
            global_fail_threshold=global_fail_threshold,
            config_file=config_file,
        )
        settings = settings or build_runtime_settings(
            profile=DECORATOR_PROFILE,
            instance_id=instance_id,
            default_source=default_source,
            backend_type=backend_type,
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
        fsm = LogicFingerprintFSM(
            instance_id=settings.instance_id,
            config=config,
            backend=backend,
        )

        self.config = config
        self.settings = settings
        self.backend = backend
        self.fsm = fsm
        self.executor = LogicFingerprintExecutor(fsm)
        self.metrics = InMemoryMetrics()
        self.context_builder = ContextBuilder(default_source=settings.default_source)
        self.event_logger = event_logger or NullEventLogger()
    def _success_response(
        self,
        validated_output: Any,
        context_dict: dict[str, Any],
        *,
        simple: bool,
    ) -> Any:
        if simple:
            return validated_output
        return {
            "ok": True,
            "result": validated_output,
            "context": context_dict,
        }

    def _error_response(
        self,
        *,
        error_code: str | None,
        error_message: str | None,
        error_details: dict[str, Any] | None,
        context_dict: dict[str, Any],
        simple: bool,
    ) -> Any:
        if simple:
            raise ProtectRuntimeError(
                error_message or "Protected call failed.",
                code=error_code,
                details=error_details or {},
                context=context_dict,
            )

        return {
            "ok": False,
            "error": {
                "code": error_code,
                "message": error_message,
                "details": error_details or {},
            },
            "context": context_dict,
        }

    def protect(
        self,
        *,
        input_model: type[BaseModel] | None = None,
        output_model: type[BaseModel] | None = None,
        simple: bool = True,
    ) -> Callable[[F], F]:
        def decorator(func: F) -> F:
            if inspect.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(
                    payload: dict[str, Any] | None = None,
                    *,
                    context: RequestContext | None = None,
                    now: float | None = None,
                ) -> Any:
                    self.metrics.record_total()

                    built_request = self.context_builder.build_request(
                        HandlerRequest(
                            payload=payload or {},
                            context=context or RequestContext(),
                        )
                    )
                    context_dict = asdict(built_request.context)

                    self.event_logger.emit(LogEvent(
                        event="protect_call_started",
                        handler=func.__name__,
                        request_id=context_dict.get("request_id"),
                        trace_id=context_dict.get("trace_id"),
                    ))

                    validated_payload = validate_input(
                        built_request.payload,
                        input_model,
                        event_logger=self.event_logger,
                        handler=func.__name__,
                        request_id=context_dict.get("request_id"),
                        trace_id=context_dict.get("trace_id"),
                    )
                    prepared_request = HandlerRequest(
                        payload=validated_payload,
                        context=built_request.context,
                    )

                    def operation() -> Any:
                        return func(prepared_request)

                    outcome = await self.executor.execute_async(operation, now=now)

                    if outcome.decision.is_probe:
                        self.metrics.record_probe()

                    if not outcome.executed:
                        self.metrics.record_blocked()
                    elif outcome.succeeded:
                        self.metrics.record_success()
                    else:
                        self.metrics.record_failure()

                    if outcome.succeeded:
                        result = outcome.result
                        validated_output = validate_output(
                            result,
                            output_model,
                            event_logger=self.event_logger,
                            handler=func.__name__,
                            request_id=context_dict.get("request_id"),
                            trace_id=context_dict.get("trace_id"),
                        )
                        self.event_logger.emit(LogEvent(
                            event="protect_call_succeeded",
                            handler=func.__name__,
                            request_id=context_dict.get("request_id"),
                            trace_id=context_dict.get("trace_id"),
                        ))
                        if is_dataclass(validated_output):
                            validated_output = asdict(validated_output)

                        return self._success_response(
                            validated_output,
                            context_dict,
                            simple=simple,
                        )
                    
                    self.event_logger.emit(LogEvent(
                        event="protect_call_failed",
                        handler=func.__name__,
                        request_id=context_dict.get("request_id"),
                        trace_id=context_dict.get("trace_id"),
                        error_code=outcome.error_code,
                        message=outcome.error_message,
                    ))

                    return self._error_response(
                        error_code=outcome.error_code,
                        error_message=outcome.error_message,
                        error_details=outcome.error_details,
                        context_dict=context_dict,
                        simple=simple,
                    )

                return async_wrapper  # type: ignore[return-value]

            @wraps(func)
            def sync_wrapper(
                payload: dict[str, Any] | None = None,
                *,
                context: RequestContext | None = None,
                now: float | None = None,
            ) -> Any:
                self.metrics.record_total()

                built_request = self.context_builder.build_request(
                    HandlerRequest(
                        payload=payload or {},
                        context=context or RequestContext(),
                    )
                )
                context_dict = asdict(built_request.context)

                self.event_logger.emit(LogEvent(
                    event="protect_call_started",
                    handler=func.__name__,
                    request_id=context_dict.get("request_id"),
                    trace_id=context_dict.get("trace_id"),
                ))

                validated_payload = validate_input(
                    built_request.payload,
                    input_model,
                    event_logger=self.event_logger,
                    handler=func.__name__,
                    request_id=context_dict.get("request_id"),
                    trace_id=context_dict.get("trace_id"),
                )
                prepared_request = HandlerRequest(
                    payload=validated_payload,
                    context=built_request.context,
                )

                def operation() -> Any:
                    return func(prepared_request)

                outcome = self.executor.execute(operation, now=now)

                if outcome.decision.is_probe:
                    self.metrics.record_probe()

                if not outcome.executed:
                    self.metrics.record_blocked()
                elif outcome.succeeded:
                    self.metrics.record_success()
                else:
                    self.metrics.record_failure()

                if outcome.succeeded:
                    result = outcome.result
                    validated_output = validate_output(
                        result,
                        output_model,
                        event_logger=self.event_logger,
                        handler=func.__name__,
                        request_id=context_dict.get("request_id"),
                        trace_id=context_dict.get("trace_id"),
                    )

                    if is_dataclass(validated_output):
                        validated_output = asdict(validated_output)
                    
                    self.event_logger.emit(LogEvent(
                        event="protect_call_succeeded",
                        handler=func.__name__,
                        request_id=context_dict.get("request_id"),
                        trace_id=context_dict.get("trace_id"),
                    ))

                    return self._success_response(
                        validated_output,
                        context_dict,
                        simple=simple,
                    )

                self.event_logger.emit(LogEvent(
                    event="protect_call_failed",
                    handler=func.__name__,
                    request_id=context_dict.get("request_id"),
                    trace_id=context_dict.get("trace_id"),
                    error_code=outcome.error_code,
                    message=outcome.error_message,
                ))

                return self._error_response(
                    error_code=outcome.error_code,
                    error_message=outcome.error_message,
                    error_details=outcome.error_details,
                    context_dict=context_dict,
                    simple=simple,
                )

            return sync_wrapper  # type: ignore[return-value]

        return decorator


def create_protector(**kwargs: Any) -> Protector:
    return Protector(**kwargs)


def protect(
    *,
    input_model: type[BaseModel] | None = None,
    output_model: type[BaseModel] | None = None,
    simple: bool = True,
) -> Callable[[F], F]:
    return Protector().protect(
        input_model=input_model,
        output_model=output_model,
        simple=simple,
    )


_package = sys.modules.get(__package__)
if _package is not None:
    setattr(_package, "protect", protect)
    setattr(_package, "create_protector", create_protector)
