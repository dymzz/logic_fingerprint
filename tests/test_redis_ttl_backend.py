from logic_fingerprint.infra.consensus import RedisTTLConsensusBackend


class FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, ex=None):
        self.store[key] = {"value": value, "ex": ex}

    def expire(self, key, ttl):
        if key in self.store:
            self.store[key]["ex"] = ttl

    def delete(self, key):
        self.store.pop(key, None)

    def exists(self, key):
        return int(key in self.store)

    def keys(self, pattern):
        prefix = pattern[:-1]
        return [k for k in self.store if k.startswith(prefix)]


def test_redis_ttl_backend_mark_heartbeat_clear():
    redis = FakeRedis()
    backend = RedisTTLConsensusBackend(redis_client=redis, ttl_seconds=30)

    backend.mark_failed("node-a")
    assert backend.is_failed("node-a") is True
    assert backend.fail_count() == 1

    backend.heartbeat("node-a")
    backend.clear_failed("node-a")
    assert backend.is_failed("node-a") is False
