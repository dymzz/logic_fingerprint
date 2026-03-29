from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeSettings:
    instance_id: str = "node-a"
    default_source: str = "api"
    backend_type: str = "memory"
    handler_registrars: tuple[str, ...] = ()
    redis_url: str | None = None
    redis_decode_responses: bool = True
    redis_key: str = "logic_fingerprint:failed_nodes"
    redis_key_prefix: str = "logic_fingerprint:failed_node"
    redis_ttl_seconds: int = 30
