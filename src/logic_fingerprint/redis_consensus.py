from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RedisConsensusBackend:
    redis_client: object
    key: str = "logic_fingerprint:failed_nodes"

    def mark_failed(self, instance_id: str) -> None:
        self.redis_client.sadd(self.key, instance_id)

    def clear_failed(self, instance_id: str) -> None:
        self.redis_client.srem(self.key, instance_id)

    def fail_count(self) -> int:
        return int(self.redis_client.scard(self.key))

    def is_failed(self, instance_id: str) -> bool:
        return bool(self.redis_client.sismember(self.key, instance_id))


@dataclass(slots=True)
class RedisTTLConsensusBackend:
    redis_client: object
    key_prefix: str = "logic_fingerprint:failed_node"
    ttl_seconds: int = 30

    def _node_key(self, instance_id: str) -> str:
        return f"{self.key_prefix}:{instance_id}"

    def mark_failed(self, instance_id: str) -> None:
        self.redis_client.set(self._node_key(instance_id), "1", ex=self.ttl_seconds)

    def heartbeat(self, instance_id: str) -> None:
        if self.is_failed(instance_id):
            self.redis_client.expire(self._node_key(instance_id), self.ttl_seconds)

    def clear_failed(self, instance_id: str) -> None:
        self.redis_client.delete(self._node_key(instance_id))

    def fail_count(self) -> int:
        keys = self.redis_client.keys(f"{self.key_prefix}:*")
        return len(keys)

    def is_failed(self, instance_id: str) -> bool:
        return bool(self.redis_client.exists(self._node_key(instance_id)))
