from logicfp.config import RuntimeConfig
from logicfp.infra.consensus import InMemoryConsensusBackend
from logicfp.domain.fsm import LogicFingerprintFSM


def build_fsm(**kwargs) -> LogicFingerprintFSM:
    config = RuntimeConfig(**kwargs)
    backend = InMemoryConsensusBackend()
    return LogicFingerprintFSM(
        instance_id="node-a",
        config=config,
        backend=backend,
    )


def test_time_driven_probe_prevents_low_qps_deadlock():
    fsm = build_fsm(
        probe_rate=0.01,
        probe_interval_seconds=10,
        consecutive_success_threshold=3,
        total_nodes=1,
        global_fail_threshold=1.0,
    )
    fsm.record_hard_fail("ERR_TIMEOUT")
    fsm.move_to_half_open()

    assert fsm.before_half_open_request(now=0)["allow_probe"] is False
    assert fsm.before_half_open_request(now=11)["allow_probe"] is True


class CountingBackend:
    def __init__(self, failed_nodes: set[str] | None = None) -> None:
        self._failed_nodes = failed_nodes or set()
        self.fail_count_calls = 0
        self.is_failed_calls = 0

    def mark_failed(self, instance_id: str) -> None:
        self._failed_nodes.add(instance_id)

    def clear_failed(self, instance_id: str) -> None:
        self._failed_nodes.discard(instance_id)

    def fail_count(self) -> int:
        self.fail_count_calls += 1
        return len(self._failed_nodes)

    def is_failed(self, instance_id: str) -> bool:
        self.is_failed_calls += 1
        return instance_id in self._failed_nodes


def test_before_request_reads_backend_status_once_per_call():
    backend = CountingBackend({"node-b"})
    fsm = LogicFingerprintFSM(
        instance_id="node-a",
        config=RuntimeConfig(total_nodes=2, global_fail_threshold=1.0),
        backend=backend,
    )

    info = fsm.before_request()

    assert info["allow_request"] is True
    assert backend.fail_count_calls == 1
    assert backend.is_failed_calls == 1


def test_before_half_open_request_reads_backend_status_once_per_call():
    backend = CountingBackend({"node-b"})
    fsm = LogicFingerprintFSM(
        instance_id="node-a",
        config=RuntimeConfig(total_nodes=2, global_fail_threshold=1.0),
        backend=backend,
    )
    fsm.move_to_half_open()

    info = fsm.before_half_open_request(now=0)

    assert info["allow_probe"] is False
    assert backend.fail_count_calls == 1
    assert backend.is_failed_calls == 1

