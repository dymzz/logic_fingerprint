from .fsm import LogicFingerprintFSM
from .metrics import InMemoryMetrics


def render_prometheus_metrics(metrics: InMemoryMetrics, fsm: LogicFingerprintFSM) -> str:
    lines = [
        "# HELP logic_fingerprint_total_requests Total execution requests.",
        "# TYPE logic_fingerprint_total_requests counter",
        f"logic_fingerprint_total_requests {metrics.total_requests}",
        "# HELP logic_fingerprint_blocked_requests Blocked requests.",
        "# TYPE logic_fingerprint_blocked_requests counter",
        f"logic_fingerprint_blocked_requests {metrics.blocked_requests}",
        "# HELP logic_fingerprint_probe_requests Probe requests.",
        "# TYPE logic_fingerprint_probe_requests counter",
        f"logic_fingerprint_probe_requests {metrics.probe_requests}",
        "# HELP logic_fingerprint_success_requests Successful requests.",
        "# TYPE logic_fingerprint_success_requests counter",
        f"logic_fingerprint_success_requests {metrics.success_requests}",
        "# HELP logic_fingerprint_failed_requests Failed requests.",
        "# TYPE logic_fingerprint_failed_requests counter",
        f"logic_fingerprint_failed_requests {metrics.failed_requests}",
        "# HELP logic_fingerprint_fsm_state FSM state as labeled gauge.",
        "# TYPE logic_fingerprint_fsm_state gauge",
        f'logic_fingerprint_fsm_state{{state="{fsm.state.value}"}} 1',
    ]
    return "\n".join(lines) + "\n"
