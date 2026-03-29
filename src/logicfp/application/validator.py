from dataclasses import asdict, is_dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from ..domain.errors import OutputValidationErrorLF, ValidationErrorLF
from ..infra.logging.event_logger import LogEvent


def validate_input(
    payload: dict[str, Any],
    model: type[BaseModel] | None,
    *,
    event_logger=None,
    handler: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    if model is None:
        return payload

    try:
        parsed = model.model_validate(payload)
        return parsed.model_dump()
    except ValidationError as exc:
        if event_logger is not None:
            event_logger.emit(LogEvent(
                event="input_validation_failed",
                handler=handler,
                request_id=request_id,
                trace_id=trace_id,
                error_code="ERR_VALIDATION",
                message="Input validation failed.",
                extra={"errors": exc.errors()},
            ))
        raise ValidationErrorLF(
            "Input validation failed.",
            details={"errors": exc.errors()},
        ) from exc


def validate_output(
    result: Any,
    model: type[BaseModel] | None,
    *,
    event_logger=None,
    handler: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
) -> Any:
    if model is None:
        return result

    raw = result
    if is_dataclass(result):
        raw = asdict(result)

    try:
        parsed = model.model_validate(raw)
        return parsed.model_dump()
    except ValidationError as exc:
        if event_logger is not None:
            event_logger.emit(LogEvent(
                event="output_validation_failed",
                handler=handler,
                request_id=request_id,
                trace_id=trace_id,
                error_code="ERR_OUTPUT_VALIDATION",
                message="Output validation failed.",
                extra={"errors": exc.errors()},
            ))
        raise OutputValidationErrorLF(
            "Output validation failed.",
            details={"errors": exc.errors()},
        ) from exc
