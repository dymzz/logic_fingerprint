from dataclasses import asdict, is_dataclass
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field
from .core.models import HandlerRequest, RequestContext
from .prometheus_metrics import render_prometheus_metrics

class ForceFailRequest(BaseModel):
    reason: str = "MANUAL_FAIL"

class ExecuteHandlerContextModel(BaseModel):
    request_id: str | None = None
    trace_id: str | None = None
    user_id: str | None = None
    source: str | None = None
    timestamp: str | None = None
    headers: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

class ExecuteHandlerRequest(BaseModel):
    handler: str
    payload: dict = Field(default_factory=dict)
    context: ExecuteHandlerContextModel = Field(default_factory=ExecuteHandlerContextModel)
    now: float | None = None

def build_router(runtime: object) -> APIRouter:
    router = APIRouter()
    fsm = runtime.fsm
    metrics = runtime.metrics

    @router.get("/")
    def root():
        return {"service": "logic-fingerprint", "state": fsm.state.value, "docs": "/docs"}

    @router.get("/favicon.ico")
    def favicon():
        return Response(status_code=204)

    @router.get("/healthz")
    def healthz():
        return {"ok": True, "state": fsm.state.value}

    @router.get("/handlers")
    def handlers():
        return {"handlers": runtime.handler_registry.names()}

    @router.get("/metrics")
    def metrics_view():
        return metrics.snapshot()

    @router.get("/metrics.prom")
    def metrics_prom():
        return Response(content=render_prometheus_metrics(metrics, fsm), media_type="text/plain; version=0.0.4")

    @router.post("/force_fail")
    def force_fail(payload: ForceFailRequest):
        fsm.record_hard_fail(payload.reason)
        return {"state": fsm.state.value, "reason": payload.reason}

    @router.post("/move_half_open")
    def move_half_open():
        fsm.move_to_half_open()
        return {"state": fsm.state.value}

    @router.post("/execute_handler")
    async def execute_handler(payload: ExecuteHandlerRequest):
        request = HandlerRequest(
            payload=payload.payload,
            context=RequestContext(
                request_id=payload.context.request_id,
                trace_id=payload.context.trace_id,
                user_id=payload.context.user_id,
                source=payload.context.source,
                timestamp=payload.context.timestamp,
                headers=payload.context.headers,
                metadata=payload.context.metadata,
            ),
        )
        outcome = await runtime.middleware.execute_handler_async(payload.handler, request=request, now=payload.now)
        if outcome.succeeded:
            result = outcome.result
            if is_dataclass(result):
                result = asdict(result)
            return {"ok": True, "result": result}
        return {"ok": False, "error": {"code": outcome.error_code, "message": outcome.error_message, "details": outcome.error_details or {}}}

    return router
