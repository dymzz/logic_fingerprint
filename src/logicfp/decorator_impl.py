from __future__ import annotations

from dataclasses import asdict, is_dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar
import inspect
import sys
import warnings

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
from .domain.errors import build_error_details, classify_exception
from .domain.ai_error_recognizer import AIErrorRecognizer
from .domain.fsm import LogicFingerprintFSM
from .domain.models import HandlerRequest, RequestContext
from .infra.consensus import build_consensus_backend
from .infra.logging import EventLogger, LogEvent, NullEventLogger

F = TypeVar("F", bound=Callable[..., Any])
_ADVANCED_PROTECTOR_KWARGS = {
    "instance_id",
    "redis_url",
    "redis_decode_responses",
    "redis_key",
    "redis_key_prefix",
    "redis_ttl_seconds",
    "config",
    "settings",
    "backend",
    "redis_client",
    "ai_error_classifier",
    "ai_error_recognizers",
    "error_action_resolver",
    "error_policy_resolver",
}


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
        ai_error_classifier: object | None = None,
        ai_error_recognizers: list[AIErrorRecognizer] | tuple[AIErrorRecognizer, ...] | None = None,
        error_action_resolver: object | None = None,
        error_policy_resolver: object | None = None,
    ) -> None:
        normalized_error_action_resolver = _resolve_error_action_resolver(
            error_action_resolver=error_action_resolver,
            error_policy_resolver=error_policy_resolver,
        )
        normalized_ai_error_recognizers = _normalize_ai_error_recognizers(ai_error_recognizers)
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
        self.executor = LogicFingerprintExecutor(
            fsm,
            ai_error_classifier=ai_error_classifier,
            ai_error_recognizers=normalized_ai_error_recognizers,
            error_action_resolver=normalized_error_action_resolver,
        )
        self.metrics = InMemoryMetrics()
        self.context_builder = ContextBuilder(default_source=settings.default_source)
        self.event_logger = event_logger or NullEventLogger()
        self.ai_error_classifier = ai_error_classifier
        self.ai_error_recognizers = normalized_ai_error_recognizers
        self.error_action_resolver = normalized_error_action_resolver
        self.error_policy_resolver = normalized_error_action_resolver
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

    def _build_error_log_extra(
        self,
        error_details: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not isinstance(error_details, dict):
            return {}
        extra: dict[str, Any] = {}
        ai_error = error_details.get("ai_error")
        if isinstance(ai_error, dict):
            ai_code = ai_error.get("code")
            if isinstance(ai_code, str):
                extra["ai_error_code"] = ai_code
            provider = ai_error.get("provider")
            if isinstance(provider, str):
                extra["provider"] = provider
        error_fact = error_details.get("error_fact")
        if isinstance(error_fact, dict):
            for key in ("stage", "source"):
                value = error_fact.get(key)
                if isinstance(value, str):
                    extra[key] = value
        error_policy = error_details.get("error_policy")
        if isinstance(error_policy, dict):
            action = error_policy.get("action")
            if isinstance(action, str):
                extra["action"] = action
        return extra

    def _handle_pre_execution_error(
        self,
        exc: Exception,
        *,
        handler_name: str,
        context_dict: dict[str, Any],
        simple: bool,
        stage_hint: str,
    ) -> Any:
        error_code = classify_exception(exc).value
        error_details = build_error_details(
            exc,
            stage_hint=stage_hint,
            ai_error_classifier=self.executor.ai_error_classifier,
            ai_error_recognizers=self.executor.ai_error_recognizers,
            error_action_resolver=self.error_action_resolver,
        )
        self.metrics.record_failure(
            error_code=error_code,
            error_details=error_details,
        )
        self.event_logger.emit(LogEvent(
            event="protect_call_failed",
            handler=handler_name,
            request_id=context_dict.get("request_id"),
            trace_id=context_dict.get("trace_id"),
            error_code=error_code,
            message=str(exc),
            extra=self._build_error_log_extra(error_details),
        ))
        return self._error_response(
            error_code=error_code,
            error_message=str(exc),
            error_details=error_details,
            context_dict=context_dict,
            simple=simple,
        )

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

                    try:
                        validated_payload = validate_input(
                            built_request.payload,
                            input_model,
                            event_logger=self.event_logger,
                            handler=func.__name__,
                            request_id=context_dict.get("request_id"),
                            trace_id=context_dict.get("trace_id"),
                        )
                    except Exception as exc:
                        return self._handle_pre_execution_error(
                            exc,
                            handler_name=func.__name__,
                            context_dict=context_dict,
                            simple=simple,
                            stage_hint="input",
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
                        self.metrics.record_blocked(
                            error_code=outcome.error_code,
                            error_details=outcome.error_details,
                        )
                    elif not outcome.succeeded:
                        self.metrics.record_failure(
                            error_code=outcome.error_code,
                            error_details=outcome.error_details,
                        )

                    if outcome.succeeded:
                        result = outcome.result
                        try:
                            validated_output = validate_output(
                                result,
                                output_model,
                                event_logger=self.event_logger,
                                handler=func.__name__,
                                request_id=context_dict.get("request_id"),
                                trace_id=context_dict.get("trace_id"),
                            )
                        except Exception as exc:
                            return self._handle_pre_execution_error(
                                exc,
                                handler_name=func.__name__,
                                context_dict=context_dict,
                                simple=simple,
                                stage_hint="output",
                            )
                        self.event_logger.emit(LogEvent(
                            event="protect_call_succeeded",
                            handler=func.__name__,
                            request_id=context_dict.get("request_id"),
                            trace_id=context_dict.get("trace_id"),
                        ))
                        self.metrics.record_success()
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
                        extra=self._build_error_log_extra(outcome.error_details),
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

                try:
                    validated_payload = validate_input(
                        built_request.payload,
                        input_model,
                        event_logger=self.event_logger,
                        handler=func.__name__,
                        request_id=context_dict.get("request_id"),
                        trace_id=context_dict.get("trace_id"),
                    )
                except Exception as exc:
                    return self._handle_pre_execution_error(
                        exc,
                        handler_name=func.__name__,
                        context_dict=context_dict,
                        simple=simple,
                        stage_hint="input",
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
                    self.metrics.record_blocked(
                        error_code=outcome.error_code,
                        error_details=outcome.error_details,
                    )
                elif not outcome.succeeded:
                    self.metrics.record_failure(
                        error_code=outcome.error_code,
                        error_details=outcome.error_details,
                    )

                if outcome.succeeded:
                    result = outcome.result
                    try:
                        validated_output = validate_output(
                            result,
                            output_model,
                            event_logger=self.event_logger,
                            handler=func.__name__,
                            request_id=context_dict.get("request_id"),
                            trace_id=context_dict.get("trace_id"),
                        )
                    except Exception as exc:
                        return self._handle_pre_execution_error(
                            exc,
                            handler_name=func.__name__,
                            context_dict=context_dict,
                            simple=simple,
                            stage_hint="output",
                        )

                    if is_dataclass(validated_output):
                        validated_output = asdict(validated_output)
                    
                    self.event_logger.emit(LogEvent(
                        event="protect_call_succeeded",
                        handler=func.__name__,
                        request_id=context_dict.get("request_id"),
                        trace_id=context_dict.get("trace_id"),
                    ))
                    self.metrics.record_success()

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
                    extra=self._build_error_log_extra(outcome.error_details),
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
    event_logger: EventLogger | None = None,
    advanced: dict[str, Any] | None = None,
    **advanced_kwargs: Any,
) -> Protector:
    unsupported = sorted(set(advanced_kwargs) - _ADVANCED_PROTECTOR_KWARGS)
    if unsupported:
        names = ", ".join(unsupported)
        raise TypeError(f"Unsupported create_protector() advanced arguments: {names}")

    if advanced is not None:
        overlap = sorted(set(advanced) & {
            "config_file",
            "probe_rate",
            "probe_interval_seconds",
            "consecutive_success_threshold",
            "total_nodes",
            "global_fail_threshold",
            "default_source",
            "backend_type",
            "event_logger",
        })
        if overlap:
            names = ", ".join(overlap)
            raise TypeError(
                "Pass user-mode create_protector() arguments directly, "
                f"not through advanced=: {names}"
            )
        invalid_advanced = sorted(set(advanced) - _ADVANCED_PROTECTOR_KWARGS)
        if invalid_advanced:
            names = ", ".join(invalid_advanced)
            raise TypeError(f"Unsupported create_protector() advanced arguments: {names}")

    merged_advanced = dict(advanced or {})
    merged_advanced.update(advanced_kwargs)

    if advanced_kwargs:
        warnings.warn(
            "Passing advanced arguments directly to create_protector() is deprecated. "
            "Use Protector(...) or create_protector(advanced={...}) for advanced control.",
            DeprecationWarning,
            stacklevel=2,
        )

    return Protector(
        config_file=config_file,
        probe_rate=probe_rate,
        probe_interval_seconds=probe_interval_seconds,
        consecutive_success_threshold=consecutive_success_threshold,
        total_nodes=total_nodes,
        global_fail_threshold=global_fail_threshold,
        default_source=default_source,
        backend_type=backend_type,
        event_logger=event_logger,
        **merged_advanced,
    )


def _resolve_error_action_resolver(
    *,
    error_action_resolver: object | None,
    error_policy_resolver: object | None,
) -> object | None:
    if error_action_resolver is not None and error_policy_resolver is not None and error_action_resolver is not error_policy_resolver:
        raise TypeError(
            "Pass only one of error_action_resolver or error_policy_resolver."
        )
    if error_policy_resolver is not None:
        warnings.warn(
            "error_policy_resolver is deprecated. Use error_action_resolver instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return error_policy_resolver
    return error_action_resolver


def _normalize_ai_error_recognizers(
    ai_error_recognizers: Iterable[AIErrorRecognizer] | None,
) -> tuple[AIErrorRecognizer, ...]:
    if ai_error_recognizers is None:
        return ()
    normalized = tuple(ai_error_recognizers)
    for recognizer in normalized:
        if not callable(recognizer):
            raise TypeError("ai_error_recognizers must contain only callables.")
    return normalized


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
