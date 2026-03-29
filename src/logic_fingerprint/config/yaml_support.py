from __future__ import annotations

from pathlib import Path
from typing import Any


def _strip_comment(line: str) -> str:
    in_single_quote = False
    in_double_quote = False
    result: list[str] = []

    for char in line:
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif char == "#" and not in_single_quote and not in_double_quote:
            break
        result.append(char)

    return "".join(result).rstrip()


def _parse_scalar(value: str) -> Any:
    stripped = value.strip()
    if stripped == "":
        return ""
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]

    lowered = stripped.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None

    try:
        if any(marker in stripped for marker in (".", "e", "E")):
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped


def parse_simple_yaml(text: str) -> dict[str, Any]:
    lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        cleaned = _strip_comment(raw_line)
        if not cleaned.strip():
            continue
        indent = len(cleaned) - len(cleaned.lstrip(" "))
        lines.append((indent, cleaned.strip()))

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for index, (indent, content) in enumerate(lines):
        while indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("Invalid YAML structure: list item without list parent.")
            parent.append(_parse_scalar(content[2:].strip()))
            continue

        if ":" not in content:
            raise ValueError(f"Invalid YAML line: {content}")

        key, raw_value = content.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not isinstance(parent, dict):
            raise ValueError("Invalid YAML structure: mapping entry without dict parent.")

        if raw_value:
            parent[key] = _parse_scalar(raw_value)
            continue

        next_container: Any = None
        for next_indent, next_content in lines[index + 1 :]:
            if next_indent <= indent:
                break
            next_container = [] if next_content.startswith("- ") else {}
            break

        parent[key] = next_container
        if next_container is not None:
            stack.append((indent, next_container))

    return root


def load_simple_yaml_file(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return parse_simple_yaml(path.read_text(encoding="utf-8"))
