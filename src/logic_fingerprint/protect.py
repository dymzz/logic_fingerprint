from __future__ import annotations

from dataclasses import asdict, is_dataclass
from functools import wraps
from typing import Any, Callable, TypeVar
import inspect

from pydantic import BaseModel

from .context_builder import ContextBuilder
from .consensus import InMemoryConsensusBackend
from .config import ProbeConfig
from .executor import LogicFingerprintExecutor
from .fsm import LogicFingerprintFSM
from .metrics import InMemoryMetrics
from .models import HandlerRequest, RequestContext
from .validator import validate_input, validate_output

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
        instance_id: str = "decorator-node",
        probe_rate: float = 0.2,
        probe_interval_seconds: float = 5.0,
        consecutive_success_threshold: int = 3,
        total_nodes: int = 1,
        global_fail_threshold: float = 1.0,
        default_source: str = "decorator",
    ) -> None:
        config = ProbeConfig(
            probe_rate=probe_rate,
            probe_interval_seconds=probe_interval_seconds,
            consecutive_success_threshold=consecutive_success_threshold,
            total_nodes=total_nodes,
            global_fail_threshold=global_fail_threshold,
        )
        backend = InMemoryConsensusBackend()
        fsm = LogicFingerprintFSM(
            instance_id=instance_id,
            config=config,
            backend=backend,
        )

        self.backend = backend
        self.fsm = fsm
        self.executor = LogicFingerprintExecutor(fsm)
        self.metrics = InMemoryMetrics()
        self.context_builder = ContextBuilder(default_source=default_source)

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

                    validated_payload = validate_input(
                        built_request.payload,
                        input_model,
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
                        validated_output = validate_output(result, output_model)

                        if is_dataclass(validated_output):
                            validated_output = asdict(validated_output)

                        return self._success_response(
                            validated_output,
                            context_dict,
                            simple=simple,
                        )

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

                validated_payload = validate_input(
                    built_request.payload,
                    input_model,
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
                    validated_output = validate_output(result, output_model)

                    if is_dataclass(validated_output):
                        validated_output = asdict(validated_output)

                    return self._success_response(
                        validated_output,
                        context_dict,
                        simple=simple,
                    )

                return self._error_response(
                    error_code=outcome.error_code,
                    error_message=outcome.error_message,
                    error_details=outcome.error_details,
                    context_dict=context_dict,
                    simple=simple,
                )

            return sync_wrapper  # type: ignore[return-value]

        return decorator


_default_protector = Protector()


def create_protector(**kwargs: Any) -> Protector:
    return Protector(**kwargs)


def protect(
    *,
    input_model: type[BaseModel] | None = None,
    output_model: type[BaseModel] | None = None,
    simple: bool = True,
) -> Callable[[F], F]:
    return _default_protector.protect(
        input_model=input_model,
        output_model=output_model,
        simple=simple,
    )