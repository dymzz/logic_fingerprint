import inspect
from dataclasses import dataclass
from .errors import ErrorCode, NullResultError, classify_exception, LogicFingerprintError
from .models import ExecutionDecision, ExecutionOutcome, FSMState, ProbeResult

@dataclass(slots=True)
class LogicFingerprintExecutor:
    fsm: object

    def _build_decision_from_closed(self):
        info = self.fsm.before_request()
        return ExecutionDecision(state=str(info["state"]), allow_request=bool(info["allow_request"]), allow_probe=bool(info["allow_probe"]), global_fail_ratio=float(info["global_fail_ratio"]), external_fail_ratio=float(info["external_fail_ratio"]), is_probe=False)
    def _build_decision_from_half_open(self, now):
        info = self.fsm.before_half_open_request(now=now)
        return ExecutionDecision(state=str(info["state"]), allow_request=bool(info["allow_request"]), allow_probe=bool(info["allow_probe"]), global_fail_ratio=float(info["global_fail_ratio"]), external_fail_ratio=float(info["external_fail_ratio"]), is_probe=bool(info["allow_probe"]))
    def _blocked_outcome(self, decision):
        return ExecutionOutcome(decision=decision, executed=False, succeeded=False, state_after=self.fsm.state.value, error_code=ErrorCode.ERR_EXECUTION_BLOCKED.value, error_message="Request blocked by FSM state.")
    def _success_outcome(self, decision, result):
        if decision.is_probe:
            self.fsm.evaluate_probe(ProbeResult(system_success=True, business_success=True))
        return ExecutionOutcome(decision=decision, executed=True, succeeded=True, state_after=self.fsm.state.value, result=result)
    def _failure_outcome(self, decision, exc):
        code = classify_exception(exc)
        details = exc.details if isinstance(exc, LogicFingerprintError) else {}
        self.fsm.record_hard_fail(code.value)
        return ExecutionOutcome(decision=decision, executed=True, succeeded=False, state_after=self.fsm.state.value, error_code=code.value, error_message=str(exc), error_details=details)
    def execute(self, operation, now=None):
        decision = self._build_decision_from_half_open(now) if self.fsm.state == FSMState.HALF_OPEN else self._build_decision_from_closed()
        if not decision.allow_request and not decision.allow_probe:
            return self._blocked_outcome(decision)
        try:
            result = operation()
            if inspect.isawaitable(result):
                raise TypeError("Async operation cannot be executed by sync execute(); use execute_async().")
            if result is None:
                raise NullResultError("Operation returned None.")
            return self._success_outcome(decision, result)
        except Exception as exc:
            return self._failure_outcome(decision, exc)
    async def execute_async(self, operation, now=None):
        decision = self._build_decision_from_half_open(now) if self.fsm.state == FSMState.HALF_OPEN else self._build_decision_from_closed()
        if not decision.allow_request and not decision.allow_probe:
            return self._blocked_outcome(decision)
        try:
            result = operation()
            if inspect.isawaitable(result):
                result = await result
            if result is None:
                raise NullResultError("Operation returned None.")
            return self._success_outcome(decision, result)
        except Exception as exc:
            return self._failure_outcome(decision, exc)
