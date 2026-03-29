from __future__ import annotations

import importlib

from ...config.runtime_settings import RuntimeSettings


def build_redis_client(*, settings: RuntimeSettings) -> object:
    if not settings.redis_url:
        raise ValueError(
            "LOGIC_FINGERPRINT_REDIS_URL is required when using a Redis backend.",
        )

    try:
        redis_module = importlib.import_module("redis")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The 'redis' package is required when backend_type is 'redis' or 'redis_ttl'.",
        ) from exc

    return redis_module.from_url(
        settings.redis_url,
        decode_responses=settings.redis_decode_responses,
    )
