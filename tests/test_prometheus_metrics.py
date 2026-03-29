from logic_fingerprint.application.metrics import InMemoryMetrics
from logic_fingerprint.config import RuntimeConfig
from logic_fingerprint.domain.fsm import LogicFingerprintFSM
from logic_fingerprint.infra.consensus import InMemoryConsensusBackend
from logic_fingerprint.infra.metrics import render_prometheus_metrics


def test_render_prometheus_metrics_contains_expected_lines():
    backend = InMemoryConsensusBackend()
    fsm = LogicFingerprintFSM(
        instance_id="node-a",
        config=RuntimeConfig(),
        backend=backend,
    )
    metrics = InMemoryMetrics(total_requests=3, success_requests=2, failed_requests=1)

    text = render_prometheus_metrics(metrics, fsm)
    assert "logic_fingerprint_total_requests 3" in text
    assert "logic_fingerprint_success_requests 2" in text
    assert 'logic_fingerprint_fsm_state{state="CLOSED"} 1' in text

