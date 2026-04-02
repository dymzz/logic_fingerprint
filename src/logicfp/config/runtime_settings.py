from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeSettings:
    instance_id: str = "decorator-node"
    default_source: str = "decorator"
    backend_type: str = "memory"
    redis_url: str | None = None
    redis_decode_responses: bool = True
    redis_key: str = "logicfp:failed_nodes"
    redis_key_prefix: str = "logicfp:failed_node"
    redis_ttl_seconds: int = 30
    handler_registrars: tuple[str, ...] = ()
