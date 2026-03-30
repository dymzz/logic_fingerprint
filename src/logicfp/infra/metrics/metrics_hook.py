from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class MetricEvent:
    metric: str
    handler: str | None = None
    value: int | float = 1
    error_code: str | None = None
    ai_error_code: str | None = None
    provider: str | None = None
    stage: str | None = None
    source: str | None = None
    action: str | None = None
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        if data["extra"] is None:
            data["extra"] = {}
        return {k: v for k, v in data.items() if v is not None}


class MetricsHook:
    def emit(self, event: MetricEvent) -> None:
        raise NotImplementedError


class NullMetricsHook(MetricsHook):
    def emit(self, event: MetricEvent) -> None:
        return


class PrintMetricsHook(MetricsHook):
    def emit(self, event: MetricEvent) -> None:
        print(event.to_dict())
