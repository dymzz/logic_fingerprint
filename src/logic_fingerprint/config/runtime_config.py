from dataclasses import dataclass


@dataclass(slots=True)
class RuntimeConfig:
    probe_rate: float = 0.2
    probe_interval_seconds: float = 5.0
    consecutive_success_threshold: int = 3
    total_nodes: int = 1
    global_fail_threshold: float = 1.0