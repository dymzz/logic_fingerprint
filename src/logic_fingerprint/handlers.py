from dataclasses import dataclass, field
from pydantic import BaseModel
from .errors import HandlerNotFoundError

@dataclass(slots=True)
class HandlerDefinition:
    func: object
    input_model: type[BaseModel] | None = None
    output_model: type[BaseModel] | None = None

@dataclass(slots=True)
class HandlerRegistry:
    _handlers: dict[str, HandlerDefinition] = field(default_factory=dict)
    def register(self, name, handler, input_model=None, output_model=None):
        self._handlers[name] = HandlerDefinition(func=handler, input_model=input_model, output_model=output_model)
    def register_decorator(self, name, input_model=None, output_model=None):
        def decorator(handler):
            self.register(name, handler, input_model=input_model, output_model=output_model)
            return handler
        return decorator
    def get(self, name):
        if name not in self._handlers:
            raise HandlerNotFoundError(f"Handler not found: {name}")
        return self._handlers[name]
    def names(self):
        return sorted(self._handlers.keys())
