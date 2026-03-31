from logicfp.application.metrics import InMemoryMetrics
from logicfp.config import RuntimeConfig
from logicfp.domain.fsm import LogicFingerprintFSM
from logicfp.infra.consensus import InMemoryConsensusBackend
from logicfp.infra.metrics import render_prometheus_metrics


def test_render_prometheus_metrics_contains_expected_lines():
    backend = InMemoryConsensusBackend()
    fsm = LogicFingerprintFSM(
        instance_id="node-a",
        config=RuntimeConfig(),
        backend=backend,
    )
    metrics = InMemoryMetrics(total_requests=3, success_requests=2, failed_requests=1)

    text = render_prometheus_metrics(metrics, fsm)
    assert "logicfp_total_requests 3" in text
    assert "logicfp_success_requests 2" in text
    assert 'logicfp_fsm_state{state="CLOSED"} 1' in text

