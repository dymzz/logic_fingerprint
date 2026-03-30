from __future__ import annotations

import pytest

from logicfp import create_protector
from logicfp.domain.models import HandlerRequest
from logicfp.infra.metrics import MetricsHook, MetricEvent, NullMetricsHook


class CollectingMetricsHook(MetricsHook):
    def __init__(self) -> None:
        self.events: list[MetricEvent] = []

    def emit(self, event: MetricEvent) -> None:
        self.events.append(event)


def test_metrics_hook_receives_success_events():
    hook = CollectingMetricsHook()
    protector = create_protector(advanced={"metrics_hook": hook})

    @protector.protect(simple=True)
    def guarded(request: HandlerRequest):
        return {"value": 1}

    guarded(payload={"x": 1})

    metrics = [e.metric for e in hook.events]
    assert "protect.total" in metrics
    assert "protect.success" in metrics
    assert "protect.failure" not in metrics


def test_metrics_hook_receives_failure_events():
    hook = CollectingMetricsHook()
    protector = create_protector(advanced={"metrics_hook": hook})

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        raise RuntimeError("boom")

    result = guarded(payload={"x": 1})

    assert result["ok"] is False
    metrics = [e.metric for e in hook.events]
    assert "protect.total" in metrics
    assert "protect.failure" in metrics
    assert "protect.success" not in metrics


def test_metrics_hook_failure_includes_dimensions():
    hook = CollectingMetricsHook()
    protector = create_protector(advanced={"metrics_hook": hook})

    class FakeRateLimitError(Exception):
        def __init__(self):
            super().__init__("TPM limit reached")
            self.status_code = 429
            self.code = "rate_limit_exceeded"

    FakeRateLimitError.__module__ = "openai"

    @protector.protect(simple=False)
    def guarded(request: HandlerRequest):
        raise FakeRateLimitError()

    guarded(payload={"x": 1})

    failure_events = [e for e in hook.events if e.metric == "protect.failure"]
    assert len(failure_events) >= 1
    evt = failure_events[0]
    assert evt.handler == "guarded"
    assert evt.ai_error_code is not None


def test_metrics_hook_receives_input_validation_failure():
    from pydantic import BaseModel

    class StrictInput(BaseModel):
        count: int

    hook = CollectingMetricsHook()
    protector = create_protector(advanced={"metrics_hook": hook})

    @protector.protect(input_model=StrictInput, simple=False)
    def guarded(request: HandlerRequest):
        return {"count": request.payload["count"]}

    result = guarded(payload={"count": "not_a_number"})

    assert result["ok"] is False
    metrics = [e.metric for e in hook.events]
    assert "protect.failure" in metrics


def test_null_metrics_hook_does_not_raise():
    hook = NullMetricsHook()
    hook.emit(MetricEvent(metric="protect.total", handler="test"))


def test_default_protector_uses_null_metrics_hook():
    protector = create_protector()
    assert isinstance(protector.metrics_hook, NullMetricsHook)
