from __future__ import annotations

from ..domain.errors import LogicExecutionError, NormalizationError, TimeoutErrorLF
from ..domain.models import HandlerRequest, HandlerResponse
from ..handler_registry import HandlerRegistry
from .schemas import SumNumbersInput, SumNumbersOutput


def _echo_payload(request: HandlerRequest) -> HandlerResponse:
    return HandlerResponse(
        ok=True,
        data={
            "payload": request.payload,
            "request_id": request.context.request_id,
            "trace_id": request.context.trace_id,
            "source": request.context.source,
            "timestamp": request.context.timestamp,
            "headers": request.context.headers,
            "metadata": request.context.metadata,
        },
    )


def _sum_numbers(request: HandlerRequest) -> HandlerResponse:
    return HandlerResponse(ok=True, data={"sum": sum(request.payload.get("numbers", []))})


def _demo_timeout(request: HandlerRequest) -> HandlerResponse:
    raise TimeoutErrorLF("simulated timeout")


def _demo_logic_error(request: HandlerRequest) -> HandlerResponse:
    raise LogicExecutionError("simulated logic failure")


def _demo_null(request: HandlerRequest) -> None:
    return None


def _demo_norm_error(request: HandlerRequest) -> HandlerResponse:
    raise NormalizationError("simulated norm failure")


async def _async_echo_payload(request: HandlerRequest) -> HandlerResponse:
    return HandlerResponse(
        ok=True,
        data={
            "payload": request.payload,
            "request_id": request.context.request_id,
            "trace_id": request.context.trace_id,
            "source": request.context.source,
            "timestamp": request.context.timestamp,
            "headers": request.context.headers,
            "metadata": request.context.metadata,
            "async": True,
        },
    )


def register_demo_handlers(handler_registry: HandlerRegistry) -> None:
    handler_registry.register("echo_payload", _echo_payload)
    handler_registry.register(
        "sum_numbers",
        _sum_numbers,
        input_model=SumNumbersInput,
        output_model=SumNumbersOutput,
    )
    handler_registry.register("demo_timeout", _demo_timeout)
    handler_registry.register("demo_logic_error", _demo_logic_error)
    handler_registry.register("demo_null", _demo_null)
    handler_registry.register("demo_norm_error", _demo_norm_error)
    handler_registry.register("async_echo_payload", _async_echo_payload)
