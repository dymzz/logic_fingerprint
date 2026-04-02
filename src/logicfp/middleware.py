from dataclasses import dataclass

from .application.context_builder import ContextBuilder
from .domain.executor import LogicFingerprintExecutor
from .domain.errors import build_error_details, classify_exception
from .handler_registry import HandlerRegistry
from .application.metrics import InMemoryMetrics
from .domain.models import ExecutionOutcome, HandlerRequest, HandlerResponse
from .application.validator import validate_input, validate_output
from .plugins import SuccessHook, apply_success_hooks


@dataclass(slots=True)
class LogicFingerprintMiddleware:
    executor: LogicFingerprintExecutor
    handler_registry: HandlerRegistry
    metrics: InMemoryMetrics
    context_builder: ContextBuilder
    success_hooks: tuple[SuccessHook, ...] = ()
    plugin_failure_mode: str = "fail_open"

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
            return HandlerResponse(
                ok=result.ok,
                data=validated,
                message=result.message,
                meta=dict(result.meta),
            )
        return validate_output(result, definition.output_model)

    def execute_handler(self, handler_name: str, request: HandlerRequest | None = None, now: float | None = None) -> ExecutionOutcome:
        self.metrics.record_total()
        execution_context: dict[str, object] = {}

        def operation():
            built_request = self.context_builder.build_request(request)
            definition = self.handler_registry.get(handler_name)
            execution_context["hook_request"] = built_request
            validated_payload = validate_input(built_request.payload, definition.input_model)
            prepared_request = HandlerRequest(payload=validated_payload, context=built_request.context)
            result = definition.func(prepared_request)
            return self._validate_result(result, definition)

        outcome = self.executor.execute(operation, now=now)
        if outcome.succeeded:
            try:
                hook_request = execution_context.get("hook_request")
                if not isinstance(hook_request, HandlerRequest):
                    raise TypeError("Middleware success hook request context is missing.")
                outcome.result, _ = apply_success_hooks(
                    request=hook_request,
                    result=outcome.result,
                    hooks=self.success_hooks,
                    plugin_failure_mode=self.plugin_failure_mode,
                )
            except Exception as exc:
                outcome.succeeded = False
                outcome.result = None
                outcome.error_code = classify_exception(exc).value
                outcome.error_message = str(exc)
                outcome.error_details = build_error_details(exc, stage_hint="plugin")
        self._record(outcome)
        return outcome

    async def execute_handler_async(self, handler_name: str, request: HandlerRequest | None = None, now: float | None = None) -> ExecutionOutcome:
        self.metrics.record_total()
        execution_context: dict[str, object] = {}

        def operation():
            built_request = self.context_builder.build_request(request)
            definition = self.handler_registry.get(handler_name)
            execution_context["hook_request"] = built_request
            validated_payload = validate_input(built_request.payload, definition.input_model)
            prepared_request = HandlerRequest(payload=validated_payload, context=built_request.context)
            execution_context["definition"] = definition
            return definition.func(prepared_request)

        outcome = await self.executor.execute_async(operation, now=now)
        if outcome.succeeded:
            try:
                definition = execution_context["definition"]
                hook_request = execution_context.get("hook_request")
                outcome.result = self._validate_result(outcome.result, definition)
                if not isinstance(hook_request, HandlerRequest):
                    raise TypeError("Middleware success hook request context is missing.")
                outcome.result, _ = apply_success_hooks(
                    request=hook_request,
                    result=outcome.result,
                    hooks=self.success_hooks,
                    plugin_failure_mode=self.plugin_failure_mode,
                )
            except Exception as exc:
                outcome.succeeded = False
                outcome.result = None
                outcome.error_code = classify_exception(exc).value
                outcome.error_message = str(exc)
                outcome.error_details = build_error_details(exc, stage_hint="plugin")
        self._record(outcome)
        return outcome

