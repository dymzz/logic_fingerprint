from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from logicfp.domain.models import HandlerRequest
from logicfp.protect import create_protector


def _make_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="logicfp-protect-", dir=Path.cwd()))


def test_protect_supports_async_functions():
    protector = create_protector()

    @protector.protect(simple=False)
    async def guarded(request: HandlerRequest):
        return {"doubled": request.payload["value"] * 2}

    result = asyncio.run(guarded(payload={"value": 21}))

    assert result["ok"] is True
    assert result["result"]["doubled"] == 42


def test_create_protector_reads_project_yaml_config_file(monkeypatch):
    workspace = _make_temp_dir()
    try:
        config_dir = workspace / "config"
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
        monkeypatch.chdir(workspace)
        monkeypatch.delenv("LOGICFP_CONFIG_FILE", raising=False)

        protector = create_protector()

        assert protector.settings.instance_id == "user-mode-node"
        assert protector.settings.default_source == "langchain"
        assert protector.config.probe_rate == 0.33
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
