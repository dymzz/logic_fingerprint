from dataclasses import asdict, is_dataclass
from pydantic import ValidationError
from .errors import OutputValidationErrorLF, ValidationErrorLF

def validate_input(payload, model):
    if model is None:
        return payload
    try:
        return model.model_validate(payload).model_dump()
    except ValidationError as exc:
        raise ValidationErrorLF("Input validation failed.", details={"errors": exc.errors()}) from exc

def validate_output(result, model):
    if model is None:
        return result
    raw = asdict(result) if is_dataclass(result) else result
    try:
        return model.model_validate(raw).model_dump()
    except ValidationError as exc:
        raise OutputValidationErrorLF("Output validation failed.", details={"errors": exc.errors()}) from exc
