from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from logicfp.config import discover_config_file
from logicfp.config.yaml_support import load_simple_yaml_file


def load_example_section(
    section_name: str,
    *,
    config_file: str | Path | None = None,
) -> dict[str, Any]:
    path = discover_config_file(config_file=config_file)
    if path is None:
        return {}

    data = load_simple_yaml_file(path)
    section = data.get(section_name, {})
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError(f"Expected '{section_name}' to be a mapping in config file.")
    return section


def _resolve_example_value(
    env_name: str,
    config_key: str,
    default: Any,
    *,
    section_values: Mapping[str, Any],
) -> Any:
    value = os.getenv(env_name)
    if value is None:
        return section_values.get(config_key, default)
    return value


def read_example_str(
    env_name: str,
    config_key: str,
    default: str,
    *,
    section_values: Mapping[str, Any],
) -> str:
    value = _resolve_example_value(
        env_name,
        config_key,
        default,
        section_values=section_values,
    )
    if value is None:
        return default
    return str(value)


def read_example_int(
    env_name: str,
    config_key: str,
    default: int,
    *,
    section_values: Mapping[str, Any],
) -> int:
    value = _resolve_example_value(
        env_name,
        config_key,
        default,
        section_values=section_values,
    )
    return int(value)


def read_example_float(
    env_name: str,
    config_key: str,
    default: float,
    *,
    section_values: Mapping[str, Any],
) -> float:
    value = _resolve_example_value(
        env_name,
        config_key,
        default,
        section_values=section_values,
    )
    return float(value)
