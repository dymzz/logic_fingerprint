from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

import logicfp.cli as cli_module

from logicfp.cli import (
    discover_cli_config_path,
    load_start_config,
    main,
    parse_simple_yaml,
)


def _make_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="logicfp-cli-", dir=Path.cwd()))


def test_parse_simple_yaml_supports_nested_sections_and_lists():
    data = parse_simple_yaml(
        """
server:
  host: 127.0.0.1
  port: 9000
app:
  demo: true
logicfp:
  backend_type: memory
  handler_registrars:
    - tests.sample_handlers
    - tests.more_handlers
"""
    )

    assert data["server"]["host"] == "127.0.0.1"
    assert data["server"]["port"] == 9000
    assert data["app"]["demo"] is True
    assert data["logicfp"]["handler_registrars"] == [
        "tests.sample_handlers",
        "tests.more_handlers",
    ]


def test_discover_cli_config_prefers_project_config_over_system_dirs(monkeypatch):
    workspace = _make_temp_dir()
    system_dir = _make_temp_dir()
    try:
        config_dir = workspace / "config"
        config_dir.mkdir()
        project_config = config_dir / "config.yaml"
        project_config.write_text("server:\n  port: 9100\n", encoding="utf-8")

        system_config = system_dir / "config.yaml"
        system_config.write_text("server:\n  port: 9200\n", encoding="utf-8")

        monkeypatch.chdir(workspace)
        discovered = discover_cli_config_path(system_dirs=[system_dir])

        assert discovered == project_config.resolve()
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
        shutil.rmtree(system_dir, ignore_errors=True)


def test_load_start_config_applies_cli_overrides():
    workspace = _make_temp_dir()
    try:
        config_path = workspace / "config.yaml"
        config_path.write_text(
            """
server:
  host: 127.0.0.1
  port: 9100
app:
  demo: false
logicfp:
  instance_id: cli-node
  handler_registrars:
    - tests.sample_handlers
""",
            encoding="utf-8",
        )

        start_config = load_start_config(
            config_path=config_path,
            port_override=9300,
            host_override="0.0.0.0",
            demo_override=True,
        )

        assert start_config.host == "0.0.0.0"
        assert start_config.port == 9300
        assert start_config.demo is True
        assert start_config.runtime_kwargs["config_file"] == str(config_path)
        assert start_config.runtime_kwargs["instance_id"] == "cli-node"
        assert start_config.runtime_kwargs["handler_registrars"] == ("tests.sample_handlers",)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_main_start_uses_demo_app_and_uvicorn(monkeypatch):
    workspace = _make_temp_dir()
    try:
        config_path = workspace / "config.yaml"
        config_path.write_text(
            """
server:
  port: 9100
logicfp:
  instance_id: demo-node
""",
            encoding="utf-8",
        )

        captured: dict[str, object] = {}

        def fake_create_demo_app(*, runtime_kwargs=None):
            captured["runtime_kwargs"] = runtime_kwargs
            return "demo-app"

        def fake_create_app(*, runtime_kwargs=None):
            captured["runtime_kwargs"] = runtime_kwargs
            return "production-app"

        def fake_uvicorn_run(app, *, host, port):
            captured["app"] = app
            captured["host"] = host
            captured["port"] = port

        monkeypatch.setattr(cli_module, "create_demo_app", fake_create_demo_app)
        monkeypatch.setattr(cli_module, "create_app", fake_create_app)
        monkeypatch.setattr(cli_module.uvicorn, "run", fake_uvicorn_run)

        exit_code = main(["start", "--config", str(config_path), "--port", "9500", "--demo"])

        assert exit_code == 0
        assert captured["app"] == "demo-app"
        assert captured["host"] == "0.0.0.0"
        assert captured["port"] == 9500
        assert captured["runtime_kwargs"] == {
            "config_file": str(config_path),
            "instance_id": "demo-node",
        }
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
