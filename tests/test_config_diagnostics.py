from __future__ import annotations

import os

import pytest

from logicfp.config import diagnose_config, describe_effective_config
from logicfp.config.runtime_config import RuntimeConfig
from logicfp.config.runtime_settings import RuntimeSettings


def test_no_warnings_for_default_config():
    warnings = diagnose_config(RuntimeConfig(), RuntimeSettings())
    assert warnings == []


def test_redis_url_ignored_when_backend_is_memory():
    settings = RuntimeSettings(backend_type="memory", redis_url="redis://localhost:6379")
    warnings = diagnose_config(RuntimeConfig(), settings)

    codes = [w["code"] for w in warnings]
    assert "REDIS_URL_IGNORED" in codes
    assert warnings[0]["level"] == "warn"


def test_redis_url_missing_when_backend_is_redis():
    settings = RuntimeSettings(backend_type="redis", redis_url=None)
    warnings = diagnose_config(RuntimeConfig(), settings)

    codes = [w["code"] for w in warnings]
    assert "REDIS_URL_MISSING" in codes
    assert any(w["level"] == "error" for w in warnings)


def test_no_warning_when_redis_backend_has_url():
    settings = RuntimeSettings(backend_type="redis", redis_url="redis://localhost:6379")
    warnings = diagnose_config(RuntimeConfig(), settings)
    codes = [w["code"] for w in warnings]
    assert "REDIS_URL_IGNORED" not in codes
    assert "REDIS_URL_MISSING" not in codes


def test_probe_rate_out_of_range():
    config = RuntimeConfig(probe_rate=1.5)
    warnings = diagnose_config(config, RuntimeSettings())

    codes = [w["code"] for w in warnings]
    assert "PROBE_RATE_OUT_OF_RANGE" in codes


def test_probe_rate_negative():
    config = RuntimeConfig(probe_rate=-0.1)
    warnings = diagnose_config(config, RuntimeSettings())

    codes = [w["code"] for w in warnings]
    assert "PROBE_RATE_OUT_OF_RANGE" in codes


def test_global_fail_threshold_out_of_range():
    config = RuntimeConfig(global_fail_threshold=2.0)
    warnings = diagnose_config(config, RuntimeSettings())

    codes = [w["code"] for w in warnings]
    assert "GLOBAL_FAIL_THRESHOLD_OUT_OF_RANGE" in codes


def test_probe_interval_non_positive():
    config = RuntimeConfig(probe_interval_seconds=0)
    warnings = diagnose_config(config, RuntimeSettings())

    codes = [w["code"] for w in warnings]
    assert "PROBE_INTERVAL_NON_POSITIVE" in codes


def test_consecutive_success_threshold_non_positive():
    config = RuntimeConfig(consecutive_success_threshold=0)
    warnings = diagnose_config(config, RuntimeSettings())

    codes = [w["code"] for w in warnings]
    assert "CONSECUTIVE_SUCCESS_THRESHOLD_NON_POSITIVE" in codes


def test_legacy_env_prefix_detected(monkeypatch):
    monkeypatch.setenv("LOGIC_FINGERPRINT_PROBE_RATE", "0.5")
    warnings = diagnose_config(RuntimeConfig(), RuntimeSettings())

    codes = [w["code"] for w in warnings]
    assert "LEGACY_ENV_PREFIX" in codes
    legacy_warning = [w for w in warnings if w["code"] == "LEGACY_ENV_PREFIX"][0]
    assert "LOGIC_FINGERPRINT_PROBE_RATE" in legacy_warning["message"]
    assert legacy_warning["level"] == "info"


def test_describe_effective_config_includes_diagnostics_key():
    result = describe_effective_config()
    assert "diagnostics" in result
    assert isinstance(result["diagnostics"], list)


def test_multiple_warnings_accumulate():
    config = RuntimeConfig(probe_rate=2.0, global_fail_threshold=-1.0)
    settings = RuntimeSettings(backend_type="redis", redis_url=None)
    warnings = diagnose_config(config, settings)

    codes = [w["code"] for w in warnings]
    assert "REDIS_URL_MISSING" in codes
    assert "PROBE_RATE_OUT_OF_RANGE" in codes
    assert "GLOBAL_FAIL_THRESHOLD_OUT_OF_RANGE" in codes
    assert len(warnings) >= 3
