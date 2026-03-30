from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pydantic")


def test_basic_function_example_returns_envelope(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.user_mode.basic_function import summarize_ticket

    result = summarize_ticket(
        payload={
            "title": "Production login failure",
            "body": "Urgent outage reported by multiple enterprise tenants.",
        }
    )

    assert result["ok"] is True
    assert result["result"]["category"] == "support_ticket"
    assert result["result"]["priority"] == "high"


def test_tool_call_example_uses_custom_protector(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.user_mode.tool_call import quote_tool

    result = quote_tool(
        payload={
            "sku": "logicfp-enterprise",
            "quantity": 2,
            "customer_tier": "enterprise",
        }
    )

    assert result["ok"] is True
    assert result["result"]["unit_price"] == 169.15
    assert result["result"]["total_price"] == 338.3


def test_exception_handling_example_raises_protect_runtime_error(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.user_mode.exception_handling import refund_order
    from logicfp.user_mode import ProtectRuntimeError

    with pytest.raises(ProtectRuntimeError, match="Refund requires manual review."):
        refund_order(payload={"order_id": "R-1001", "amount": 6000})


def test_config_diagnostics_describes_effective_decorator_config(monkeypatch, tmp_path: Path):
    workspace = tmp_path
    config_dir = workspace / "config"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        """
logicfp:
  instance_id: doc-node
  default_source: docs
  probe_rate: 0.45
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace)

    from logicfp.config import DECORATOR_PROFILE, describe_effective_config

    description = describe_effective_config(profile=DECORATOR_PROFILE)

    assert description["config_file"] == str((config_dir / "config.yaml").resolve())
    assert description["runtime_config"]["probe_rate"] == 0.45
    assert description["runtime_settings"]["instance_id"] == "doc-node"
    assert description["runtime_settings"]["default_source"] == "docs"


def test_action_resolver_example_can_drive_fallback(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.user_mode.action_resolver import (
        fetch_inventory_snapshot,
        fetch_inventory_with_fallback,
    )

    result = fetch_inventory_snapshot(payload={"warehouse": "cn-east-1"})

    assert result["ok"] is False
    assert result["error"]["details"]["error_policy"]["action"] == "fallback"

    fallback = fetch_inventory_with_fallback({"warehouse": "cn-east-1"})

    assert fallback["source"] == "local-fallback"
    assert fallback["stale"] is True


def test_custom_recognizer_example_maps_private_provider_error(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(repo_root))
    monkeypatch.syspath_prepend(str(repo_root / "src"))

    from examples.user_mode.custom_recognizer import (
        fetch_model_summary,
        fetch_model_summary_with_fallback,
    )

    result = fetch_model_summary(payload={"topic": "release-notes"})

    assert result["ok"] is False
    assert result["error"]["details"]["ai_error"]["code"] == "UPSTREAM_OVERLOADED"
    assert result["error"]["details"]["ai_error"]["provider"] == "openai"
    assert result["error"]["details"]["error_policy"]["action"] == "retry"

    fallback = fetch_model_summary_with_fallback({"topic": "release-notes"})

    assert fallback["source"] == "local-cache"
    assert fallback["stale"] is True
