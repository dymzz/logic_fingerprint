from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

from logic_fingerprint.domain.models import HandlerRequest
from logic_fingerprint.runtime import build_production_runtime


def _make_temp_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="logicfingerprint-business-skeleton-", dir=Path.cwd()))


def test_business_skeleton_registrar_loads_and_executes(monkeypatch):
    workspace = _make_temp_dir()
    try:
        config_dir = workspace / "config"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(
            """
business:
  inventory_source: erp-cache
  pricing_currency: USD
  stock_offset: 3
  default_discount_rate: 0.10
""".strip()
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]))
        monkeypatch.chdir(workspace)
        monkeypatch.delenv("LOGIC_FINGERPRINT_CONFIG_FILE", raising=False)
        monkeypatch.delenv("BUSINESS_INVENTORY_SOURCE", raising=False)
        monkeypatch.delenv("BUSINESS_PRICING_CURRENCY", raising=False)
        monkeypatch.delenv("BUSINESS_STOCK_OFFSET", raising=False)
        monkeypatch.delenv("BUSINESS_DEFAULT_DISCOUNT_RATE", raising=False)

        runtime = build_production_runtime(
            handler_registrars=("examples.business_skeleton.handlers.register",),
        )

        inventory_outcome = runtime.middleware.execute_handler(
            "inventory_lookup",
            request=HandlerRequest(payload={"sku": "SKU-1001", "warehouse": "overflow"}),
        )
        quote_outcome = asyncio.run(
            runtime.middleware.execute_handler_async(
                "order_quote",
                request=HandlerRequest(
                    payload={"order_id": "ORDER-100", "items": [10, 15, 5]},
                ),
            )
        )

        assert runtime.handler_registry.names() == ["inventory_lookup", "order_quote"]
        assert inventory_outcome.succeeded is True
        assert inventory_outcome.result.data["source"] == "erp-cache"
        assert inventory_outcome.result.data["quantity"] == 28
        assert quote_outcome.succeeded is True
        assert quote_outcome.result.data["currency"] == "USD"
        assert quote_outcome.result.data["discount"] == 3.0
        assert quote_outcome.result.data["total"] == 27.0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
