from ...application.metrics import InMemoryMetrics
from ...domain.fsm import LogicFingerprintFSM


def render_prometheus_metrics(metrics: InMemoryMetrics, fsm: LogicFingerprintFSM) -> str:
    lines = [
        "# HELP logicfp_total_requests Total execution requests.",
        "# TYPE logicfp_total_requests counter",
        f"logicfp_total_requests {metrics.total_requests}",
        "# HELP logicfp_blocked_requests Blocked requests.",
        "# TYPE logicfp_blocked_requests counter",
        f"logicfp_blocked_requests {metrics.blocked_requests}",
        "# HELP logicfp_probe_requests Probe requests.",
        "# TYPE logicfp_probe_requests counter",
        f"logicfp_probe_requests {metrics.probe_requests}",
        "# HELP logicfp_success_requests Successful requests.",
        "# TYPE logicfp_success_requests counter",
        f"logicfp_success_requests {metrics.success_requests}",
        "# HELP logicfp_failed_requests Failed requests.",
        "# TYPE logicfp_failed_requests counter",
        f"logicfp_failed_requests {metrics.failed_requests}",
        "# HELP logicfp_fsm_state FSM state as labeled gauge.",
        "# TYPE logicfp_fsm_state gauge",
        f'logicfp_fsm_state{{state="{fsm.state.value}"}} 1',
    ]
    return "\n".join(lines) + "\n"


