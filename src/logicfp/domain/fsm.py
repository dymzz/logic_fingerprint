from dataclasses import dataclass, field
from typing import Optional
import time
from ..config import RuntimeConfig
from .models import FSMState, ProbeResult

@dataclass(slots=True)
class LogicFingerprintFSM:
    instance_id: str
    config: RuntimeConfig
    backend: object
    state: FSMState = FSMState.CLOSED
    request_counter: int = 0
    success_count: int = 0
    last_probe_time: float = field(default_factory=lambda: 0.0)
    last_failure_reason: Optional[str] = None

    @property
    def probe_every_n_requests(self) -> int:
        return max(1, int(1 / self.config.probe_rate))
    @property
    def global_fail_ratio(self) -> float:
        return self.backend.fail_count() / self.config.total_nodes
    @property
    def external_fail_count(self) -> int:
        return self.backend.fail_count() - int(self.backend.is_failed(self.instance_id))
    @property
    def external_fail_ratio(self) -> float:
        return self.external_fail_count / self.config.total_nodes
    def should_force_global_open(self) -> bool:
        return self.external_fail_ratio >= self.config.global_fail_threshold
    def _backend_ratios(self) -> tuple[float, float]:
        failed_nodes = self.backend.fail_count()
        local_failed = int(self.backend.is_failed(self.instance_id))
        global_fail_ratio = failed_nodes / self.config.total_nodes
        external_fail_ratio = (failed_nodes - local_failed) / self.config.total_nodes
        return global_fail_ratio, external_fail_ratio
    def record_hard_fail(self, reason: str = "HARD_FAIL") -> None:
        self.state = FSMState.OPEN
        self.success_count = 0
        self.last_failure_reason = reason
        self.backend.mark_failed(self.instance_id)
    def move_to_half_open(self) -> None:
        self.state = FSMState.HALF_OPEN
        self.success_count = 0
    def close(self) -> None:
        self.state = FSMState.CLOSED
        self.success_count = 0
        self.last_failure_reason = None
        self.backend.clear_failed(self.instance_id)
    def should_allow_probe(self, now=None) -> bool:
        now = time.time() if now is None else now
        self.request_counter += 1
        if self.state != FSMState.HALF_OPEN:
            return False
        by_request = (self.request_counter % self.probe_every_n_requests) == 0
        by_time = (now - self.last_probe_time) >= self.config.probe_interval_seconds
        if by_request or by_time:
            self.last_probe_time = now
            return True
        return False
    def evaluate_probe(self, result: ProbeResult):
        if self.state != FSMState.HALF_OPEN:
            return self.state
        if result.probe_success:
            self.success_count += 1
        else:
            self.success_count = 0
            self.record_hard_fail(reason="PROBE_FAILED")
            return self.state
        if self.success_count >= self.config.consecutive_success_threshold:
            self.close()
        return self.state
    def before_request(self):
        global_fail_ratio, external_fail_ratio = self._backend_ratios()
        if external_fail_ratio >= self.config.global_fail_threshold:
            self.state = FSMState.OPEN
        return {"state": self.state.value, "allow_request": self.state == FSMState.CLOSED, "allow_probe": False, "global_fail_ratio": global_fail_ratio, "external_fail_ratio": external_fail_ratio}
    def before_half_open_request(self, now=None):
        global_fail_ratio, external_fail_ratio = self._backend_ratios()
        if external_fail_ratio >= self.config.global_fail_threshold:
            self.state = FSMState.OPEN
            return {"state": self.state.value, "allow_request": False, "allow_probe": False, "global_fail_ratio": global_fail_ratio, "external_fail_ratio": external_fail_ratio}
        allow_probe = self.should_allow_probe(now=now)
        return {"state": self.state.value, "allow_request": False, "allow_probe": allow_probe, "global_fail_ratio": global_fail_ratio, "external_fail_ratio": external_fail_ratio}
