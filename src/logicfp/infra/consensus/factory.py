from __future__ import annotations

from ...config.runtime_settings import RuntimeSettings
from .client import build_redis_client
from .memory import InMemoryConsensusBackend
from .redis import RedisConsensusBackend, RedisTTLConsensusBackend


def build_consensus_backend(
    *,
    settings: RuntimeSettings,
    redis_client: object | None = None,
) -> object:
    if settings.backend_type == "memory":
        return InMemoryConsensusBackend()
    if redis_client is None:
        redis_client = build_redis_client(settings=settings)
    if settings.backend_type == "redis":
        return RedisConsensusBackend(redis_client=redis_client, key=settings.redis_key)
    if settings.backend_type == "redis_ttl":
        return RedisTTLConsensusBackend(
            redis_client=redis_client,
            key_prefix=settings.redis_key_prefix,
            ttl_seconds=settings.redis_ttl_seconds,
        )
    raise ValueError(f"Unsupported backend_type: {settings.backend_type}")
