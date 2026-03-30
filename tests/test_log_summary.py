from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from logicfp.infra.logging.log_summary import format_log_summary, summarize_jsonl_logs


def test_summarize_jsonl_logs_reads_rotated_files_in_time_order() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root / ".tmp" / f"logicfp-log-summary-{uuid4().hex}"
    base = workspace / "logs" / "logicfp.jsonl"
    base.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_event(
            base.with_name("logicfp.jsonl.2"),
            {"event": "protect_call_started", "extra": {}},
        )
        _write_event(
            base.with_name("logicfp.jsonl.1"),
            {
                "event": "protect_call_failed",
                "error_code": "ERR_UNKNOWN",
                "extra": {
                    "ai_error_code": "RATE_LIMIT_TOKEN",
                    "provider": "openai",
                    "stage": "dependency",
                    "source": "dependency",
                    "action": "retry",
                },
            },
        )
        _write_event(
            base,
            {
                "event": "protect_call_failed",
                "error_code": "ERR_UNKNOWN",
                "extra": {
                    "ai_error_code": "UPSTREAM_OVERLOADED",
                    "provider": "anthropic",
                    "stage": "dependency",
                    "source": "dependency",
                    "action": "retry",
                },
            },
        )

        summary = summarize_jsonl_logs(base)

        assert summary.total_events == 3
        assert summary.files[-1].endswith("logicfp.jsonl")
        assert summary.counts["event"]["protect_call_failed"] == 2
        assert summary.counts["ai_error_code"]["RATE_LIMIT_TOKEN"] == 1
        assert summary.counts["ai_error_code"]["UPSTREAM_OVERLOADED"] == 1
        assert summary.counts["provider"]["openai"] == 1
        assert summary.counts["provider"]["anthropic"] == 1
        assert summary.hotspots["RATE_LIMIT_TOKEN | openai | retry"] == 1
        assert summary.hotspots["UPSTREAM_OVERLOADED | anthropic | retry"] == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_summarize_jsonl_logs_limit_only_counts_recent_events() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root / ".tmp" / f"logicfp-log-summary-limit-{uuid4().hex}"
    base = workspace / "logs" / "logicfp.jsonl"
    base.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_event(
            base.with_name("logicfp.jsonl.2"),
            {"event": "protect_call_failed", "extra": {"action": "warn"}},
        )
        _write_event(
            base.with_name("logicfp.jsonl.1"),
            {"event": "protect_call_failed", "extra": {"action": "retry"}},
        )
        _write_event(
            base,
            {"event": "protect_call_failed", "extra": {"action": "fallback"}},
        )

        summary = summarize_jsonl_logs(base, limit=2)

        assert summary.total_events == 2
        assert "warn" not in summary.counts.get("action", {})
        assert summary.counts["action"]["retry"] == 1
        assert summary.counts["action"]["fallback"] == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_format_log_summary_renders_human_readable_text() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root / ".tmp" / f"logicfp-log-summary-format-{uuid4().hex}"
    base = workspace / "logs" / "logicfp.jsonl"
    base.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_event(
            base,
            {
                "event": "protect_call_failed",
                "error_code": "ERR_UNKNOWN",
                "extra": {
                    "ai_error_code": "UPSTREAM_OVERLOADED",
                    "provider": "openai",
                    "stage": "dependency",
                    "source": "dependency",
                    "action": "retry",
                },
            },
        )

        output = format_log_summary(summarize_jsonl_logs(base), top=3)

        assert "Files: 1" in output
        assert "Events: 1" in output
        assert "hotspots:" in output
        assert "UPSTREAM_OVERLOADED | openai | retry: 1" in output
        assert "ai_error_code:" in output
        assert "UPSTREAM_OVERLOADED: 1" in output
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_summarize_jsonl_logs_hotspots_fall_back_to_error_code_without_ai_code() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root / ".tmp" / f"logicfp-log-summary-hotspots-{uuid4().hex}"
    base = workspace / "logs" / "logicfp.jsonl"
    base.parent.mkdir(parents=True, exist_ok=True)
    try:
        _write_event(
            base,
            {
                "event": "protect_call_failed",
                "error_code": "ERR_VALIDATION",
                "extra": {
                    "stage": "input",
                    "source": "caller",
                    "action": "block",
                },
            },
        )

        summary = summarize_jsonl_logs(base)

        assert summary.hotspots["ERR_VALIDATION | - | block"] == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _write_event(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
