from __future__ import annotations

import asyncio
import importlib
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from logicfp.domain.models import HandlerRequest
from logicfp import create_protector


def test_protect_supports_async_functions():
    protector = create_protector()

    @protector.protect(simple=False)
    async def guarded(request: HandlerRequest):
        return {"doubled": request.payload["value"] * 2}

    result = asyncio.run(guarded(payload={"value": 21}))

    assert result["ok"] is True
    assert result["result"]["doubled"] == 42


def test_create_protector_reads_project_yaml_config_file(monkeypatch, tmp_path: Path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        """
logicfp:
  instance_id: user-mode-node
  default_source: langchain
  probe_rate: 0.33
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)

    protector = create_protector()

    assert protector.settings.instance_id == "user-mode-node"
    assert protector.settings.default_source == "langchain"
    assert protector.config.probe_rate == 0.33


def test_root_protect_creates_isolated_default_protectors():
    root_protect = importlib.import_module("logicfp").__dict__["protect"]

    @root_protect(simple=True)
    def always_fail(request: HandlerRequest):
        raise ValueError("boom")

    @root_protect(simple=False)
    def still_runs(request: HandlerRequest):
        return {"value": request.payload["value"] * 2}

    with pytest.raises(Exception, match="boom"):
        always_fail(payload={"value": 1})

    result = still_runs(payload={"value": 21})

    assert result["ok"] is True
    assert result["result"]["value"] == 42
