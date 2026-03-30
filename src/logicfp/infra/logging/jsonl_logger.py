from __future__ import annotations

import json
from pathlib import Path

from .event_logger import EventLogger, LogEvent


class JsonlEventLogger(EventLogger):
    def __init__(
        self,
        path: str | Path,
        *,
        max_bytes: int | None = None,
        backup_count: int = 3,
    ) -> None:
        if max_bytes is not None and max_bytes <= 0:
            raise ValueError("max_bytes must be positive when provided.")
        if backup_count < 0:
            raise ValueError("backup_count must be zero or positive.")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    def emit(self, event: LogEvent) -> None:
        payload = event.to_dict()
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        self._rotate_if_needed(line)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def _rotate_if_needed(self, line: str) -> None:
        if self.max_bytes is None:
            return
        current_size = self.path.stat().st_size if self.path.exists() else 0
        incoming_size = len(line.encode("utf-8"))
        if current_size + incoming_size <= self.max_bytes:
            return
        self._rotate_files()

    def _rotate_files(self) -> None:
        if not self.path.exists():
            return
        if self.backup_count == 0:
            self.path.unlink(missing_ok=True)
            return

        oldest = self._backup_path(self.backup_count)
        if oldest.exists():
            oldest.unlink()

        for index in range(self.backup_count - 1, 0, -1):
            source = self._backup_path(index)
            target = self._backup_path(index + 1)
            if source.exists():
                source.replace(target)

        self.path.replace(self._backup_path(1))

    def _backup_path(self, index: int) -> Path:
        return self.path.with_name(f"{self.path.name}.{index}")
