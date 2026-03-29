import shutil
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from logicfp.config import (
    API_PROFILE,
    DECORATOR_PROFILE,
    build_runtime_settings,
    load_runtime_settings_from_env,
)


def _make_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="logicfp-settings-", dir=Path.cwd()))
from logicfp.infra.consensus import (
    InMemoryConsensusBackend,
    build_consensus_backend,
    build_redis_client,
)


def test_build_runtime_settings_uses_profile_defaults():
    api_settings = build_runtime_settings(profile=API_PROFILE)
    decorator_settings = build_runtime_settings(profile=DECORATOR_PROFILE)

    assert api_settings.instance_id == "node-a"
    assert api_settings.default_source == "api"
    assert decorator_settings.instance_id == "decorator-node"
    assert decorator_settings.default_source == "decorator"


def test_load_runtime_settings_from_env_reads_backend_fields(monkeypatch):
    monkeypatch.setenv("LOGICFP_INSTANCE_ID", "node-b")
    monkeypatch.setenv("LOGICFP_DEFAULT_SOURCE", "gateway")
    monkeypatch.setenv("LOGICFP_BACKEND_TYPE", "memory")
    monkeypatch.setenv(
        "LOGICFP_HANDLER_REGISTRARS",
        "tests.sample_handlers:register_handlers, tests.more_handlers",
    )
    monkeypatch.setenv("LOGICFP_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("LOGICFP_REDIS_TTL_SECONDS", "45")

    settings = load_runtime_settings_from_env()

    assert settings.instance_id == "node-b"
    assert settings.default_source == "gateway"
    assert settings.backend_type == "memory"
    assert settings.handler_registrars == (
        "tests.sample_handlers:register_handlers",
        "tests.more_handlers",
    )
    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.redis_ttl_seconds == 45


def test_build_runtime_settings_explicit_args_override_environment(monkeypatch):
    monkeypatch.setenv("LOGICFP_INSTANCE_ID", "node-b")
    monkeypatch.setenv("LOGICFP_DEFAULT_SOURCE", "gateway")
    monkeypatch.setenv("LOGICFP_HANDLER_REGISTRARS", "tests.sample_handlers")
    monkeypatch.setenv("LOGICFP_REDIS_URL", "redis://localhost:6379/0")

    settings = build_runtime_settings(
        instance_id="node-c",
        default_source="worker",
        handler_registrars=("tests.custom_handlers:register_handlers",),
        redis_url="redis://cache.internal:6379/1",
    )

    assert settings.instance_id == "node-c"
    assert settings.default_source == "worker"
    assert settings.handler_registrars == ("tests.custom_handlers:register_handlers",)
    assert settings.redis_url == "redis://cache.internal:6379/1"


def test_load_runtime_settings_reads_project_yaml_config_file(monkeypatch):
    workspace = _make_temp_dir()
    try:
        config_dir = workspace / "config"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(
            """
logicfp:
  instance_id: project-node
  default_source: langchain
  backend_type: memory
  handler_registrars:
    - tests.sample_handlers
""".strip()
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(workspace)
        monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)
        monkeypatch.delenv("LOGICFP_INSTANCE_ID", raising=False)
        monkeypatch.delenv("LOGICFP_DEFAULT_SOURCE", raising=False)
        monkeypatch.delenv("LOGICFP_BACKEND_TYPE", raising=False)
        monkeypatch.delenv("LOGICFP_HANDLER_REGISTRARS", raising=False)

        settings = load_runtime_settings_from_env()

        assert settings.instance_id == "project-node"
        assert settings.default_source == "langchain"
        assert settings.backend_type == "memory"
        assert settings.handler_registrars == ("tests.sample_handlers",)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_build_runtime_settings_supports_explicit_yaml_config_file(monkeypatch):
    workspace = _make_temp_dir()
    try:
        config_path = workspace / "custom.yaml"
        config_path.write_text(
            """
logicfp:
  instance_id: file-node
  default_source: file-source
""".strip()
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)

        settings = build_runtime_settings(config_file=config_path)

        assert settings.instance_id == "file-node"
        assert settings.default_source == "file-source"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_build_consensus_backend_creates_memory_backend():
    settings = build_runtime_settings()

    backend = build_consensus_backend(settings=settings)

    assert isinstance(backend, InMemoryConsensusBackend)


def test_build_redis_client_requires_url():
    settings = build_runtime_settings(backend_type="redis", redis_url=None)

    with pytest.raises(ValueError):
        build_redis_client(settings=settings)


def test_build_consensus_backend_requires_redis_dependency():
    settings = build_runtime_settings(
        backend_type="redis",
        redis_url="redis://localhost:6379/0",
    )

    with pytest.raises(RuntimeError):
        build_consensus_backend(settings=settings)
