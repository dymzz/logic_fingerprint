from logic_fingerprint.config import RuntimeConfig
from logic_fingerprint.infra.consensus import InMemoryConsensusBackend
from logic_fingerprint.domain.fsm import LogicFingerprintFSM


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

