from dataclasses import dataclass
from .config import ProbeConfig
from .consensus import InMemoryConsensusBackend
from .context_builder import ContextBuilder
from .executor import LogicFingerprintExecutor
from .fsm import LogicFingerprintFSM
from .handlers import HandlerRegistry
from .heartbeat import HeartbeatService
from .input_models import SumNumbersInput
from .metrics import InMemoryMetrics
from .middleware import LogicFingerprintMiddleware
from .output_models import SumNumbersOutput
from .errors import TimeoutErrorLF, LogicExecutionError, NormalizationError
from .models import HandlerRequest, HandlerResponse

@dataclass(slots=True)
class LogicFingerprintRuntime:
    backend: object
    fsm: object
    executor: object
    metrics: object
    handler_registry: object
    middleware: object
    heartbeat: object
    context_builder: object

def build_runtime() -> LogicFingerprintRuntime:
    config = ProbeConfig(probe_rate=0.2, probe_interval_seconds=5.0, consecutive_success_threshold=3, total_nodes=1, global_fail_threshold=1.0)
    backend = InMemoryConsensusBackend()
    fsm = LogicFingerprintFSM(instance_id="node-a", config=config, backend=backend)
    executor = LogicFingerprintExecutor(fsm)
    metrics = InMemoryMetrics()
    handler_registry = HandlerRegistry()
    heartbeat = HeartbeatService(backend=backend, instance_id="node-a")
    context_builder = ContextBuilder(default_source="api")
    middleware = LogicFingerprintMiddleware(executor=executor, handler_registry=handler_registry, metrics=metrics, context_builder=context_builder)

    handler_registry.register("echo_payload", lambda request: HandlerResponse(ok=True, data={"payload": request.payload, "request_id": request.context.request_id, "trace_id": request.context.trace_id, "source": request.context.source, "timestamp": request.context.timestamp, "headers": request.context.headers, "metadata": request.context.metadata}))
    handler_registry.register("sum_numbers", lambda request: HandlerResponse(ok=True, data={"sum": sum(request.payload.get("numbers", []))}), input_model=SumNumbersInput, output_model=SumNumbersOutput)
    handler_registry.register("demo_timeout", lambda request: (_ for _ in ()).throw(TimeoutErrorLF("simulated timeout")))
    handler_registry.register("demo_logic_error", lambda request: (_ for _ in ()).throw(LogicExecutionError("simulated logic failure")))
    handler_registry.register("demo_null", lambda request: None)
    handler_registry.register("demo_norm_error", lambda request: (_ for _ in ()).throw(NormalizationError("simulated norm failure")))

    @handler_registry.register_decorator("async_echo_payload")
    async def async_echo_payload(request: HandlerRequest):
        return HandlerResponse(ok=True, data={"payload": request.payload, "request_id": request.context.request_id, "trace_id": request.context.trace_id, "source": request.context.source, "timestamp": request.context.timestamp, "headers": request.context.headers, "metadata": request.context.metadata, "async": True})

    return LogicFingerprintRuntime(backend=backend, fsm=fsm, executor=executor, metrics=metrics, handler_registry=handler_registry, middleware=middleware, heartbeat=heartbeat, context_builder=context_builder)
