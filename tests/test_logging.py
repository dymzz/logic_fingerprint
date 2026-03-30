from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from logicfp.infra.logging import (
    EventLogger,
    JsonlEventLogger,
    LogEvent,
    MultiEventLogger,
    SummaryLogger,
)


class RecorderLogger(EventLogger):
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def emit(self, event: LogEvent) -> None:
        self.events.append(event.to_dict())


def test_jsonl_event_logger_writes_json_lines() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root / ".tmp" / f"logicfp-logging-{uuid4().hex}"
    path = workspace / "logs" / "logicfp.jsonl"
    logger = JsonlEventLogger(path)
    try:
        logger.emit(
            LogEvent(
                event="protect_call_failed",
                error_code="ERR_UNKNOWN",
                extra={"ai_error_code": "UPSTREAM_OVERLOADED", "action": "retry"},
            )
        )

        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["event"] == "protect_call_failed"
        assert payload["error_code"] == "ERR_UNKNOWN"
        assert payload["extra"]["ai_error_code"] == "UPSTREAM_OVERLOADED"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_jsonl_event_logger_rotates_by_file_size() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root / ".tmp" / f"logicfp-logging-rotate-{uuid4().hex}"
    path = workspace / "logs" / "logicfp.jsonl"
    logger = JsonlEventLogger(path, max_bytes=120, backup_count=2)
    try:
        logger.emit(LogEvent(event="protect_call_failed", message="x" * 80))
        logger.emit(LogEvent(event="protect_call_failed", message="y" * 80))

        assert path.exists()
        rotated = path.with_name("logicfp.jsonl.1")
        assert rotated.exists()

        current_lines = path.read_text(encoding="utf-8").splitlines()
        rotated_lines = rotated.read_text(encoding="utf-8").splitlines()
        assert len(current_lines) == 1
        assert len(rotated_lines) == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_jsonl_event_logger_rotation_can_drop_backups() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root / ".tmp" / f"logicfp-logging-nobackup-{uuid4().hex}"
    path = workspace / "logs" / "logicfp.jsonl"
    logger = JsonlEventLogger(path, max_bytes=120, backup_count=0)
    try:
        logger.emit(LogEvent(event="protect_call_failed", message="x" * 80))
        logger.emit(LogEvent(event="protect_call_failed", message="y" * 80))

        assert path.exists()
        assert not path.with_name("logicfp.jsonl.1").exists()
        assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_summary_logger_aggregates_counts_and_flushes_to_sink() -> None:
    sink = RecorderLogger()
    logger = SummaryLogger(every_n=2, sink=sink)

    logger.emit(
        LogEvent(
            event="protect_call_failed",
            error_code="ERR_UNKNOWN",
            extra={
                "ai_error_code": "UPSTREAM_OVERLOADED",
                "stage": "dependency",
                "source": "dependency",
                "action": "retry",
            },
        )
    )
    logger.emit(
        LogEvent(
            event="protect_call_failed",
            error_code="ERR_UNKNOWN",
            extra={
                "ai_error_code": "UPSTREAM_OVERLOADED",
                "stage": "dependency",
                "source": "dependency",
                "action": "retry",
            },
        )
    )

    assert len(sink.events) == 1
    summary = sink.events[0]
    assert summary["event"] == "logicfp_summary"
    counts = summary["extra"]["counts"]
    assert counts["event:protect_call_failed"] == 2
    assert counts["error_code:ERR_UNKNOWN"] == 2
    assert counts["ai_error_code:UPSTREAM_OVERLOADED"] == 2
    assert counts["stage:dependency"] == 2
    assert counts["source:dependency"] == 2
    assert counts["action:retry"] == 2


def test_multi_event_logger_fans_out_to_all_targets() -> None:
    first = RecorderLogger()
    second = RecorderLogger()
    logger = MultiEventLogger(first, second)

    logger.emit(LogEvent(event="protect_call_started", handler="demo"))

    assert len(first.events) == 1
    assert len(second.events) == 1
    assert first.events[0]["event"] == "protect_call_started"
    assert second.events[0]["handler"] == "demo"
