from __future__ import annotations

import json
from pathlib import Path

from .event_logger import EventLogger, LogEvent


class JsonlEventLogger(EventLogger):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: LogEvent) -> None:
        payload = event.to_dict()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
