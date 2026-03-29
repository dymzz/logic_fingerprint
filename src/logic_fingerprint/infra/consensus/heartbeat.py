from dataclasses import dataclass

@dataclass(slots=True)
class HeartbeatService:
    backend: object
    instance_id: str
    def beat(self) -> None:
        heartbeat = getattr(self.backend, "heartbeat", None)
        if callable(heartbeat):
            heartbeat(self.instance_id)
