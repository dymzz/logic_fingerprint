from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class LogEvent:
    event: str
    handler: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    state: str | None = None
    strategy: str | None = None
    error_code: str | None = None
    message: str | None = None
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        if data["extra"] is None:
            data["extra"] = {}
        return data


class EventLogger:
    def emit(self, event: LogEvent) -> None:
        raise NotImplementedError


class NullEventLogger(EventLogger):
    def emit(self, event: LogEvent) -> None:
        return


class PrintEventLogger(EventLogger):
    def emit(self, event: LogEvent) -> None:
        print(event.to_dict())