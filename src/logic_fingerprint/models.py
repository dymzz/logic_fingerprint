from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class FSMState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

@dataclass(slots=True)
class ProbeResult:
    system_success: bool
    business_success: bool
    @property
    def probe_success(self) -> bool:
        return self.system_success and self.business_success

@dataclass(slots=True)
class ExecutionDecision:
    state: str
    allow_request: bool
    allow_probe: bool
    global_fail_ratio: float
    external_fail_ratio: float
    is_probe: bool

@dataclass(slots=True)
class ExecutionOutcome:
    decision: ExecutionDecision
    executed: bool
    succeeded: bool
    state_after: str
    result: Any = None
    error_code: str | None = None
    error_message: str | None = None
    error_details: dict[str, Any] | None = None

@dataclass(slots=True)
class RequestContext:
    request_id: str | None = None
    trace_id: str | None = None
    user_id: str | None = None
    source: str | None = None
    timestamp: str | None = None
    headers: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(slots=True)
class HandlerRequest:
    payload: dict[str, Any] = field(default_factory=dict)
    context: RequestContext = field(default_factory=RequestContext)

@dataclass(slots=True)
class HandlerResponse:
    ok: bool
    data: Any = None
    message: str | None = None
