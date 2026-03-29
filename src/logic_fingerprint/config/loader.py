from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from .runtime_config import RuntimeConfig
from .runtime_settings import RuntimeSettings
from .yaml_support import load_simple_yaml_file


DEFAULT_ENV_PREFIX = "LOGIC_FINGERPRINT_"
DEFAULT_CONFIG_DIR_NAME = "config"
DEFAULT_CONFIG_FILE_NAME = "config.yaml"
API_PROFILE = "api"
DECORATOR_PROFILE = "decorator"


def _resolve_value(
    env_name: str,
    config_key: str,
    default: Any,
    *,
    file_values: Mapping[str, Any],
) -> Any:
    value = os.getenv(env_name)
    if value is None:
        return file_values.get(config_key, default)
    return value


def _read_float(
    env_name: str,
    config_key: str,
    default: float,
    *,
    file_values: Mapping[str, Any],
) -> float:
    value = _resolve_value(env_name, config_key, default, file_values=file_values)
    return float(value)


def _read_int(
    env_name: str,
    config_key: str,
    default: int,
    *,
    file_values: Mapping[str, Any],
) -> int:
    value = _resolve_value(env_name, config_key, default, file_values=file_values)
    return int(value)


def _read_str(
    env_name: str,
    config_key: str,
    default: str,
    *,
    file_values: Mapping[str, Any],
) -> str:
    value = _resolve_value(env_name, config_key, default, file_values=file_values)
    if value is None:
        return default
    return str(value)


def _read_optional_str(
    env_name: str,
    config_key: str,
    default: str | None,
    *,
    file_values: Mapping[str, Any],
) -> str | None:
    value = _resolve_value(env_name, config_key, default, file_values=file_values)
    if value is None:
        return default
    if value == "":
        return None
    return str(value)


def _read_bool(
    env_name: str,
    config_key: str,
    default: bool,
    *,
    file_values: Mapping[str, Any],
) -> bool:
    value = _resolve_value(env_name, config_key, default, file_values=file_values)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _read_tuple(
    env_name: str,
    config_key: str,
    default: tuple[str, ...],
    *,
    file_values: Mapping[str, Any],
) -> tuple[str, ...]:
    value = _resolve_value(env_name, config_key, default, file_values=file_values)
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if str(item).strip())
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _normalize_config_path(path: str | Path) -> Path:
    normalized = Path(path).expanduser()
    if normalized.is_absolute():
        return normalized
    return (Path.cwd() / normalized).resolve()


def _extract_logic_fingerprint_values(data: dict[str, Any]) -> dict[str, Any]:
    for section_name in ("logic_fingerprint", "logicfingerprint"):
        section = data.get(section_name)
        if section is None:
            continue
        if not isinstance(section, dict):
            raise ValueError(f"Expected '{section_name}' to be a mapping in config file.")
        return section
    return data


def discover_config_file(
    *,
    config_file: str | Path | None = None,
    prefix: str = DEFAULT_ENV_PREFIX,
    start_dir: str | Path | None = None,
) -> Path | None:
    if config_file is not None:
        explicit_path = _normalize_config_path(config_file)
        if not explicit_path.is_file():
            raise FileNotFoundError(f"Logic Fingerprint config file not found: {explicit_path}")
        return explicit_path

    env_override = os.getenv(f"{prefix}CONFIG_FILE")
    if env_override is not None:
        env_override = env_override.strip()
        if not env_override:
            return None
        explicit_path = _normalize_config_path(env_override)
        if not explicit_path.is_file():
            raise FileNotFoundError(f"Logic Fingerprint config file not found: {explicit_path}")
        return explicit_path

    current_dir = Path(start_dir or Path.cwd()).resolve()
    for directory in (current_dir, *current_dir.parents):
        for candidate in (
            directory / DEFAULT_CONFIG_DIR_NAME / DEFAULT_CONFIG_FILE_NAME,
            directory / DEFAULT_CONFIG_FILE_NAME,
        ):
            if candidate.is_file():
                return candidate
    return None


def load_config_file_values(
    *,
    config_file: str | Path | None = None,
    prefix: str = DEFAULT_ENV_PREFIX,
    start_dir: str | Path | None = None,
) -> dict[str, Any]:
    path = discover_config_file(
        config_file=config_file,
        prefix=prefix,
        start_dir=start_dir,
    )
    if path is None:
        return {}
    return _extract_logic_fingerprint_values(load_simple_yaml_file(path))


def _default_runtime_settings(profile: str) -> RuntimeSettings:
    if profile == DECORATOR_PROFILE:
        return RuntimeSettings(instance_id="decorator-node", default_source="decorator")
    return RuntimeSettings()


def load_runtime_config_from_env(
    *,
    prefix: str = DEFAULT_ENV_PREFIX,
    config_file: str | Path | None = None,
    start_dir: str | Path | None = None,
) -> RuntimeConfig:
    defaults = RuntimeConfig()
    file_values = load_config_file_values(
        config_file=config_file,
        prefix=prefix,
        start_dir=start_dir,
    )
    return RuntimeConfig(
        probe_rate=_read_float(
            f"{prefix}PROBE_RATE",
            "probe_rate",
            defaults.probe_rate,
            file_values=file_values,
        ),
        probe_interval_seconds=_read_float(
            f"{prefix}PROBE_INTERVAL_SECONDS",
            "probe_interval_seconds",
            defaults.probe_interval_seconds,
            file_values=file_values,
        ),
        consecutive_success_threshold=_read_int(
            f"{prefix}CONSECUTIVE_SUCCESS_THRESHOLD",
            "consecutive_success_threshold",
            defaults.consecutive_success_threshold,
            file_values=file_values,
        ),
        total_nodes=_read_int(
            f"{prefix}TOTAL_NODES",
            "total_nodes",
            defaults.total_nodes,
            file_values=file_values,
        ),
        global_fail_threshold=_read_float(
            f"{prefix}GLOBAL_FAIL_THRESHOLD",
            "global_fail_threshold",
            defaults.global_fail_threshold,
            file_values=file_values,
        ),
    )


def build_runtime_config(
    *,
    probe_rate: float | None = None,
    probe_interval_seconds: float | None = None,
    consecutive_success_threshold: int | None = None,
    total_nodes: int | None = None,
    global_fail_threshold: float | None = None,
    prefix: str = DEFAULT_ENV_PREFIX,
    config_file: str | Path | None = None,
    start_dir: str | Path | None = None,
) -> RuntimeConfig:
    config = load_runtime_config_from_env(
        prefix=prefix,
        config_file=config_file,
        start_dir=start_dir,
    )
    overrides: dict[str, float | int] = {}

    if probe_rate is not None:
        overrides["probe_rate"] = probe_rate
    if probe_interval_seconds is not None:
        overrides["probe_interval_seconds"] = probe_interval_seconds
    if consecutive_success_threshold is not None:
        overrides["consecutive_success_threshold"] = consecutive_success_threshold
    if total_nodes is not None:
        overrides["total_nodes"] = total_nodes
    if global_fail_threshold is not None:
        overrides["global_fail_threshold"] = global_fail_threshold

    if not overrides:
        return config
    return replace(config, **overrides)


def load_runtime_settings_from_env(
    *,
    profile: str = API_PROFILE,
    prefix: str = DEFAULT_ENV_PREFIX,
    config_file: str | Path | None = None,
    start_dir: str | Path | None = None,
) -> RuntimeSettings:
    defaults = _default_runtime_settings(profile)
    file_values = load_config_file_values(
        config_file=config_file,
        prefix=prefix,
        start_dir=start_dir,
    )
    return RuntimeSettings(
        instance_id=_read_str(
            f"{prefix}INSTANCE_ID",
            "instance_id",
            defaults.instance_id,
            file_values=file_values,
        ),
        default_source=_read_str(
            f"{prefix}DEFAULT_SOURCE",
            "default_source",
            defaults.default_source,
            file_values=file_values,
        ),
        backend_type=_read_str(
            f"{prefix}BACKEND_TYPE",
            "backend_type",
            defaults.backend_type,
            file_values=file_values,
        ),
        handler_registrars=_read_tuple(
            f"{prefix}HANDLER_REGISTRARS",
            "handler_registrars",
            defaults.handler_registrars,
            file_values=file_values,
        ),
        redis_url=_read_optional_str(
            f"{prefix}REDIS_URL",
            "redis_url",
            defaults.redis_url,
            file_values=file_values,
        ),
        redis_decode_responses=_read_bool(
            f"{prefix}REDIS_DECODE_RESPONSES",
            "redis_decode_responses",
            defaults.redis_decode_responses,
            file_values=file_values,
        ),
        redis_key=_read_str(
            f"{prefix}REDIS_KEY",
            "redis_key",
            defaults.redis_key,
            file_values=file_values,
        ),
        redis_key_prefix=_read_str(
            f"{prefix}REDIS_KEY_PREFIX",
            "redis_key_prefix",
            defaults.redis_key_prefix,
            file_values=file_values,
        ),
        redis_ttl_seconds=_read_int(
            f"{prefix}REDIS_TTL_SECONDS",
            "redis_ttl_seconds",
            defaults.redis_ttl_seconds,
            file_values=file_values,
        ),
    )


def build_runtime_settings(
    *,
    profile: str = API_PROFILE,
    instance_id: str | None = None,
    default_source: str | None = None,
    backend_type: str | None = None,
    handler_registrars: tuple[str, ...] | None = None,
    redis_url: str | None = None,
    redis_decode_responses: bool | None = None,
    redis_key: str | None = None,
    redis_key_prefix: str | None = None,
    redis_ttl_seconds: int | None = None,
    prefix: str = DEFAULT_ENV_PREFIX,
    config_file: str | Path | None = None,
    start_dir: str | Path | None = None,
) -> RuntimeSettings:
    settings = load_runtime_settings_from_env(
        profile=profile,
        prefix=prefix,
        config_file=config_file,
        start_dir=start_dir,
    )
    overrides: dict[str, str | int | bool | tuple[str, ...]] = {}

    if instance_id is not None:
        overrides["instance_id"] = instance_id
    if default_source is not None:
        overrides["default_source"] = default_source
    if backend_type is not None:
        overrides["backend_type"] = backend_type
    if handler_registrars is not None:
        overrides["handler_registrars"] = handler_registrars
    if redis_url is not None:
        overrides["redis_url"] = redis_url
    if redis_decode_responses is not None:
        overrides["redis_decode_responses"] = redis_decode_responses
    if redis_key is not None:
        overrides["redis_key"] = redis_key
    if redis_key_prefix is not None:
        overrides["redis_key_prefix"] = redis_key_prefix
    if redis_ttl_seconds is not None:
        overrides["redis_ttl_seconds"] = redis_ttl_seconds

    if not overrides:
        return settings
    return replace(settings, **overrides)
