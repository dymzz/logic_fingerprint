from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

import uvicorn

from .config import DEFAULT_CONFIG_FILE_NAME
from .config.yaml_support import load_simple_yaml_file, parse_simple_yaml
from .engineering import create_app, create_demo_app


CLI_CONFIG_FILENAMES = (DEFAULT_CONFIG_FILE_NAME,)

RUNTIME_KWARG_KEYS = (
    "instance_id",
    "default_source",
    "backend_type",
    "handler_registrars",
    "redis_url",
    "redis_decode_responses",
    "redis_key",
    "redis_key_prefix",
    "redis_ttl_seconds",
    "probe_rate",
    "probe_interval_seconds",
    "consecutive_success_threshold",
    "total_nodes",
    "global_fail_threshold",
)


@dataclass(slots=True)
class StartConfig:
    host: str = "0.0.0.0"
    port: int = 8000
    demo: bool = False
    config_path: Path | None = None
    runtime_kwargs: dict[str, Any] = field(default_factory=dict)

def _iter_project_config_candidates(start_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for directory in (start_dir, *start_dir.parents):
        for filename in CLI_CONFIG_FILENAMES:
            candidates.append(directory / "config" / filename)
        for filename in CLI_CONFIG_FILENAMES:
            candidates.append(directory / filename)
    return candidates


def _iter_system_config_dirs() -> list[Path]:
    system_dirs = [
        Path("/etc/logic_fingerprint"),
        Path("/etc/logicfingerprint"),
    ]

    for env_name in ("PROGRAMDATA", "APPDATA", "LOCALAPPDATA"):
        value = os.getenv(env_name)
        if not value:
            continue
        base_dir = Path(value)
        system_dirs.append(base_dir / "logic_fingerprint")
        system_dirs.append(base_dir / "logicfingerprint")

    return system_dirs


def discover_cli_config_path(
    explicit_path: str | Path | None = None,
    *,
    start_dir: str | Path | None = None,
    system_dirs: Sequence[Path] | None = None,
) -> Path | None:
    if explicit_path is not None:
        resolved = Path(explicit_path).expanduser()
        if not resolved.is_absolute():
            resolved = (Path.cwd() / resolved).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"CLI config file not found: {resolved}")
        return resolved

    current_dir = Path(start_dir or Path.cwd()).resolve()
    for candidate in _iter_project_config_candidates(current_dir):
        if candidate.is_file():
            return candidate.resolve()

    for system_dir in system_dirs or _iter_system_config_dirs():
        if not system_dir.is_dir():
            continue
        for filename in CLI_CONFIG_FILENAMES:
            candidate = system_dir / filename
            if candidate.is_file():
                return candidate.resolve()

    return None


def load_cli_config(path: Path | None) -> dict[str, Any]:
    return load_simple_yaml_file(path)


def _read_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Expected '{key}' to be a mapping in CLI config.")
    return value


def _normalize_runtime_kwargs(data: dict[str, Any]) -> dict[str, Any]:
    runtime_kwargs: dict[str, Any] = {}
    logic_fingerprint = _read_mapping(data, "logic_fingerprint")

    for key in RUNTIME_KWARG_KEYS:
        value = logic_fingerprint.get(key)
        if value is None and key in data:
            value = data[key]
        if value is None:
            continue
        if key == "handler_registrars":
            if isinstance(value, list):
                value = tuple(str(item) for item in value)
            elif isinstance(value, str):
                value = tuple(item.strip() for item in value.split(",") if item.strip())
        runtime_kwargs[key] = value

    return runtime_kwargs


def load_start_config(
    *,
    config_path: Path | None,
    port_override: int | None = None,
    host_override: str | None = None,
    demo_override: bool = False,
) -> StartConfig:
    data = load_cli_config(config_path)
    server = _read_mapping(data, "server")
    app = _read_mapping(data, "app")

    host = host_override or str(server.get("host", "0.0.0.0"))
    port = port_override if port_override is not None else int(server.get("port", 8000))
    demo = demo_override or bool(app.get("demo", data.get("demo", False)))

    return StartConfig(
        host=host,
        port=port,
        demo=demo,
        config_path=config_path,
        runtime_kwargs={
            **({"config_file": str(config_path)} if config_path is not None else {}),
            **_normalize_runtime_kwargs(data),
        },
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="logicfingerprint")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start the HTTP service.")
    start_parser.add_argument("--host", help="Bind host. Defaults to config or 0.0.0.0.")
    start_parser.add_argument(
        "--port",
        type=int,
        help="Bind port. Defaults to config or 8000.",
    )
    start_parser.add_argument(
        "--config",
        help="Path to CLI YAML config. Explicit path has the highest priority.",
    )
    start_parser.add_argument(
        "--demo",
        action="store_true",
        help="Start in demo mode.",
    )
    return parser


def start_command(args: argparse.Namespace) -> int:
    config_path = discover_cli_config_path(args.config)
    start_config = load_start_config(
        config_path=config_path,
        port_override=args.port,
        host_override=args.host,
        demo_override=args.demo,
    )

    if start_config.config_path is not None:
        print(f"Using CLI config: {start_config.config_path}")

    mode = "demo" if start_config.demo else "production"
    print(
        f"Starting Logic Fingerprint HTTP service on "
        f"{start_config.host}:{start_config.port} ({mode})"
    )

    app = (
        create_demo_app(runtime_kwargs=start_config.runtime_kwargs)
        if start_config.demo
        else create_app(runtime_kwargs=start_config.runtime_kwargs)
    )
    uvicorn.run(app, host=start_config.host, port=start_config.port)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "start":
        return start_command(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
