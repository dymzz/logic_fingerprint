from dataclasses import dataclass

from .context_builder import ContextBuilder
from .executor import LogicFingerprintExecutor
from .handlers import HandlerRegistry
from .metrics import InMemoryMetrics
from .models import ExecutionOutcome, HandlerRequest, HandlerResponse
from .validator import validate_input, validate_output


@dataclass(slots=True)
class LogicFingerprintMiddleware:
    executor: LogicFingerprintExecutor
    handler_registry: HandlerRegistry
    metrics: InMemoryMetrics
    context_builder: ContextBuilder

    def _record(self, outcome: ExecutionOutcome) -> None:
        if outcome.decision.is_probe:
            self.metrics.record_probe()
        if not outcome.executed:
            self.metrics.record_blocked()
        elif outcome.succeeded:
            self.metrics.record_success()
        else:
            self.metrics.record_failure()

    def _validate_result(self, result, definition):
        if isinstance(result, HandlerResponse):
            validated = validate_output(result.data, definition.output_model)
            return HandlerResponse(ok=result.ok, data=validated, message=result.message)
        return validate_output(result, definition.output_model)

    def execute_handler(self, handler_name: str, request: HandlerRequest | None = None, now: float | None = None) -> ExecutionOutcome:
        self.metrics.record_total()

        def operation():
            built_request = self.context_builder.build_request(request)
            definition = self.handler_registry.get(handler_name)
            validated_payload = validate_input(built_request.payload, definition.input_model)
            prepared_request = HandlerRequest(payload=validated_payload, context=built_request.context)
            result = definition.func(prepared_request)
            return self._validate_result(result, definition)

        outcome = self.executor.execute(operation, now=now)
        self._record(outcome)
        return outcome

    async def execute_handler_async(self, handler_name: str, request: HandlerRequest | None = None, now: float | None = None) -> ExecutionOutcome:
        self.metrics.record_total()

        def operation():
            built_request = self.context_builder.build_request(request)
            definition = self.handler_registry.get(handler_name)
            validated_payload = validate_input(built_request.payload, definition.input_model)
            prepared_request = HandlerRequest(payload=validated_payload, context=built_request.context)
            return definition.func(prepared_request)

        outcome = await self.executor.execute_async(operation, now=now)
        if outcome.succeeded:
            built_request = self.context_builder.build_request(request)
            definition = self.handler_registry.get(handler_name)
            outcome.result = self._validate_result(outcome.result, definition)
        self._record(outcome)
        return outcome
