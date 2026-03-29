from dataclasses import dataclass, asdict

@dataclass(slots=True)
class InMemoryMetrics:
    total_requests: int = 0
    blocked_requests: int = 0
    probe_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    def record_total(self): self.total_requests += 1
    def record_blocked(self): self.blocked_requests += 1
    def record_probe(self): self.probe_requests += 1
    def record_success(self): self.success_requests += 1
    def record_failure(self): self.failed_requests += 1
    def snapshot(self): return asdict(self)
