from dataclasses import dataclass

@dataclass(slots=True)
class ProbeConfig:
    probe_rate: float = 0.1
    probe_interval_seconds: float = 10.0
    consecutive_success_threshold: int = 3
    total_nodes: int = 1
    global_fail_threshold: float = 1.0
