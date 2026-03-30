from __future__ import annotations

from collections import Counter
from typing import Any

from .event_logger import EventLogger, LogEvent, PrintEventLogger


class SummaryLogger(EventLogger):
    def __init__(
        self,
        *,
        every_n: int = 20,
        sink: EventLogger | None = None,
    ) -> None:
        if every_n <= 0:
            raise ValueError("every_n must be positive.")
        self.every_n = every_n
        self.sink = sink or PrintEventLogger()
        self._pending = 0
        self._counts = Counter[str]()

    def emit(self, event: LogEvent) -> None:
        self._pending += 1
        self._update_counts(event)
        if self._pending >= self.every_n:
            self.flush()

    def flush(self) -> None:
        if self._pending == 0:
            return
        summary = {
            "window_size": self._pending,
            "counts": dict(sorted(self._counts.items())),
        }
        self.sink.emit(
            LogEvent(
                event="logicfp_summary",
                message="Aggregated logicfp event summary.",
                extra=summary,
            )
        )
        self._pending = 0
        self._counts.clear()

    def _update_counts(self, event: LogEvent) -> None:
        self._counts[f"event:{event.event}"] += 1
        if event.error_code:
            self._counts[f"error_code:{event.error_code}"] += 1

        extra = event.extra if isinstance(event.extra, dict) else {}
        for key in ("ai_error_code", "stage", "source", "action"):
            value = extra.get(key)
            if isinstance(value, str) and value:
                self._counts[f"{key}:{value}"] += 1


class MultiEventLogger(EventLogger):
    def __init__(self, *loggers: EventLogger) -> None:
        self.loggers = tuple(logger for logger in loggers if logger is not None)

    def emit(self, event: LogEvent) -> None:
        for logger in self.loggers:
            logger.emit(event)

    def flush(self) -> None:
        for logger in self.loggers:
            flush = getattr(logger, "flush", None)
            if callable(flush):
                flush()
