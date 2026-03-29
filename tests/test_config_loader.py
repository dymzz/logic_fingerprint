import shutil
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from logicfp.config import (
    build_runtime_config,
    discover_config_file,
    load_runtime_config_from_env,
)


def _make_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="logicfp-config-", dir=Path.cwd()))


def test_build_runtime_config_uses_defaults_without_env(monkeypatch):
    monkeypatch.delenv("LOGICFP_PROBE_RATE", raising=False)
    monkeypatch.delenv("LOGICFP_TOTAL_NODES", raising=False)

    config = build_runtime_config()

    assert config.probe_rate == 0.2
    assert config.total_nodes == 1


def test_load_runtime_config_from_env_reads_environment(monkeypatch):
    monkeypatch.setenv("LOGICFP_PROBE_RATE", "0.45")
    monkeypatch.setenv("LOGICFP_TOTAL_NODES", "5")

    config = load_runtime_config_from_env()

    assert config.probe_rate == 0.45
    assert config.total_nodes == 5


def test_build_runtime_config_explicit_args_override_environment(monkeypatch):
    monkeypatch.setenv("LOGICFP_PROBE_RATE", "0.45")
    monkeypatch.setenv("LOGICFP_TOTAL_NODES", "5")

    config = build_runtime_config(probe_rate=0.9, total_nodes=2)

    assert config.probe_rate == 0.9
    assert config.total_nodes == 2


def test_load_runtime_config_reads_project_yaml_config_file(monkeypatch):
    workspace = _make_temp_dir()
    try:
        config_dir = workspace / "config"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text(
            """
logicfp:
  probe_rate: 0.35
  total_nodes: 4
""".strip()
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(workspace)
        monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)
        monkeypatch.delenv("LOGICFP_PROBE_RATE", raising=False)
        monkeypatch.delenv("LOGICFP_TOTAL_NODES", raising=False)

        config = load_runtime_config_from_env()

        assert config.probe_rate == 0.35
        assert config.total_nodes == 4
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_discover_config_file_walks_up_from_nested_directory(monkeypatch):
    workspace = _make_temp_dir()
    try:
        config_dir = workspace / "config"
        config_dir.mkdir()
        config_path = config_dir / "config.yaml"
        config_path.write_text(
            "logicfp:\n  probe_rate: 0.25\n",
            encoding="utf-8",
        )
        nested_dir = workspace / "src" / "app"
        nested_dir.mkdir(parents=True)
        monkeypatch.chdir(nested_dir)
        monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)

        discovered = discover_config_file()

        assert discovered == config_path
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_environment_overrides_project_yaml_config_file(monkeypatch):
    workspace = _make_temp_dir()
    try:
        config_dir = workspace / "config"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(
            "logicfp:\n  probe_rate: 0.35\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(workspace)
        monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)
        monkeypatch.setenv("LOGICFP_PROBE_RATE", "0.55")

        config = load_runtime_config_from_env()

        assert config.probe_rate == 0.55
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
