from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUMMARY_KEYS: tuple[str, ...] = (
    "event",
    "error_code",
    "ai_error_code",
    "provider",
    "stage",
    "source",
    "action",
)


@dataclass(frozen=True)
class LogSummary:
    files: list[str]
    total_events: int
    counts: dict[str, dict[str, int]]
    hotspots: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "files": list(self.files),
            "total_events": self.total_events,
            "counts": {key: dict(value) for key, value in self.counts.items()},
            "hotspots": dict(self.hotspots),
        }


def summarize_jsonl_logs(
    path: str | Path,
    *,
    limit: int | None = None,
    include_rotated: bool = True,
) -> LogSummary:
    files = discover_log_files(path, include_rotated=include_rotated)
    events = [event for file_path in files for event in _read_jsonl_events(file_path)]
    if limit is not None:
        events = events[-limit:]

    buckets = {key: Counter[str]() for key in SUMMARY_KEYS}
    hotspots = Counter[str]()
    for event in events:
        extra = event.get("extra")
        extra_dict = extra if isinstance(extra, dict) else {}
        _count_value(buckets["event"], event.get("event"))
        _count_value(buckets["error_code"], event.get("error_code"))
        _count_value(buckets["ai_error_code"], extra_dict.get("ai_error_code"))
        _count_value(buckets["provider"], extra_dict.get("provider"))
        _count_value(buckets["stage"], extra_dict.get("stage"))
        _count_value(buckets["source"], extra_dict.get("source"))
        _count_value(buckets["action"], extra_dict.get("action"))
        hotspot = _build_hotspot_label(event, extra_dict)
        if hotspot is not None:
            hotspots[hotspot] += 1

    return LogSummary(
        files=[str(file_path) for file_path in files],
        total_events=len(events),
        counts={key: dict(counter) for key, counter in buckets.items() if counter},
        hotspots=dict(hotspots),
    )


def discover_log_files(path: str | Path, *, include_rotated: bool = True) -> list[Path]:
    base_path = Path(path)
    if not include_rotated:
        return [base_path] if base_path.exists() else []

    parent = base_path.parent if str(base_path.parent) else Path(".")
    pattern = f"{base_path.name}*"
    discovered = [
        candidate
        for candidate in parent.glob(pattern)
        if candidate.is_file() and _is_log_member(base_path.name, candidate.name)
    ]
    discovered.sort(key=_log_sort_key)
    return discovered


def format_log_summary(summary: LogSummary, *, top: int = 5) -> str:
    lines = [
        f"Files: {len(summary.files)}",
        f"Events: {summary.total_events}",
    ]
    if summary.files:
        lines.append("Paths:")
        lines.extend(f"  {path}" for path in summary.files)

    if summary.hotspots:
        lines.append("hotspots:")
        sorted_hotspots = sorted(summary.hotspots.items(), key=lambda item: (-item[1], item[0]))
        for name, count in sorted_hotspots[:top]:
            lines.append(f"  {name}: {count}")

    for key in SUMMARY_KEYS:
        values = summary.counts.get(key)
        if not values:
            continue
        lines.append(f"{key}:")
        sorted_items = sorted(values.items(), key=lambda item: (-item[1], item[0]))
        for name, count in sorted_items[:top]:
            lines.append(f"  {name}: {count}")
    return "\n".join(lines)


def _read_jsonl_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _count_value(counter: Counter[str], value: Any) -> None:
    if isinstance(value, str) and value:
        counter[value] += 1


def _build_hotspot_label(event: dict[str, Any], extra: dict[str, Any]) -> str | None:
    ai_error_code = extra.get("ai_error_code")
    error_code = event.get("error_code")
    action = extra.get("action")
    provider = extra.get("provider")

    primary = ai_error_code if isinstance(ai_error_code, str) and ai_error_code else None
    if primary is None and isinstance(error_code, str) and error_code:
        primary = error_code
    if primary is None:
        return None

    provider_label = provider if isinstance(provider, str) and provider else "-"
    action_label = action if isinstance(action, str) and action else "-"
    return f"{primary} | {provider_label} | {action_label}"


def _is_log_member(base_name: str, candidate_name: str) -> bool:
    if candidate_name == base_name:
        return True
    if not candidate_name.startswith(f"{base_name}."):
        return False
    suffix = candidate_name[len(base_name) + 1 :]
    return suffix.isdigit()


def _log_sort_key(path: Path) -> tuple[int, int]:
    name = path.name
    if "." not in name:
        return (10_000, 0)
    suffix = name.rsplit(".", 1)[-1]
    if suffix.isdigit():
        return (-int(suffix), 0)
    return (10_000, 0)
