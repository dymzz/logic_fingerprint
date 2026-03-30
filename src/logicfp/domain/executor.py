import inspect
from dataclasses import dataclass
from .error_report import build_error_report
from .errors import ErrorCode, NullResultError, build_error_details, classify_exception
from .models import ExecutionDecision, ExecutionOutcome, FSMState, ProbeResult

@dataclass(slots=True)
class LogicFingerprintExecutor:
    fsm: object
    ai_error_classifier: object | None = None
    ai_error_recognizers: tuple[object, ...] = ()
    error_action_resolver: object | None = None

    def _build_decision_from_closed(self):
        info = self.fsm.before_request()
        return ExecutionDecision(state=str(info["state"]), allow_request=bool(info["allow_request"]), allow_probe=bool(info["allow_probe"]), global_fail_ratio=float(info["global_fail_ratio"]), external_fail_ratio=float(info["external_fail_ratio"]), is_probe=False)
    def _build_decision_from_half_open(self, now):
        info = self.fsm.before_half_open_request(now=now)
        return ExecutionDecision(state=str(info["state"]), allow_request=bool(info["allow_request"]), allow_probe=bool(info["allow_probe"]), global_fail_ratio=float(info["global_fail_ratio"]), external_fail_ratio=float(info["external_fail_ratio"]), is_probe=bool(info["allow_probe"]))
    def _blocked_outcome(self, decision):
        report = build_error_report(
            code=ErrorCode.ERR_EXECUTION_BLOCKED.value,
            message="Request blocked by FSM state.",
            stage_hint="execute",
            details={},
            action_resolver=self.error_action_resolver,
        )
        return ExecutionOutcome(
            decision=decision,
            executed=False,
            succeeded=False,
            state_after=self.fsm.state.value,
            error_code=ErrorCode.ERR_EXECUTION_BLOCKED.value,
            error_message="Request blocked by FSM state.",
            error_details={
                "error_fact": report.fact.as_dict(),
                "error_policy": report.policy.as_dict(),
            },
        )
    def _success_outcome(self, decision, result):
        if decision.is_probe:
            self.fsm.evaluate_probe(ProbeResult(system_success=True, business_success=True))
        return ExecutionOutcome(decision=decision, executed=True, succeeded=True, state_after=self.fsm.state.value, result=result)
    def _failure_outcome(self, decision, exc):
        code = classify_exception(exc)
        details = build_error_details(
            exc,
            stage_hint="execute",
            ai_error_classifier=self.ai_error_classifier,
            ai_error_recognizers=self.ai_error_recognizers,
            error_action_resolver=self.error_action_resolver,
        )
        self.fsm.record_hard_fail(code.value)
        return ExecutionOutcome(decision=decision, executed=True, succeeded=False, state_after=self.fsm.state.value, error_code=code.value, error_message=str(exc), error_details=details)

    def _is_empty_ai_result(self, result):
        if result is None:
            return True, {"empty_result_signals": ["result_none"]}

        if isinstance(result, dict):
            empty_fields = []
            ai_text_fields = ("content", "text", "output_text", "completion")
            for name in ai_text_fields:
                if name in result and _is_empty_value(result[name]):
                    empty_fields.append(name)
            if empty_fields:
                return True, {"empty_result_signals": ["empty_text_fields"], "empty_fields": empty_fields}
            if "choices" in result and isinstance(result["choices"], list) and not result["choices"]:
                return True, {"empty_result_signals": ["empty_choices"]}
            if "content_blocks" in result and isinstance(result["content_blocks"], list) and not result["content_blocks"]:
                return True, {"empty_result_signals": ["empty_content_blocks"]}

        return False, {}

    def execute(self, operation, now=None):
        decision = self._build_decision_from_half_open(now) if self.fsm.state == FSMState.HALF_OPEN else self._build_decision_from_closed()
        if not decision.allow_request and not decision.allow_probe:
            return self._blocked_outcome(decision)
        try:
            result = operation()
            if inspect.isawaitable(result):
                raise TypeError("Async operation cannot be executed by sync execute(); use execute_async().")
            is_empty_result, details = self._is_empty_ai_result(result)
            if is_empty_result:
                raise NullResultError("Operation returned an empty result.", details=details)
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
            is_empty_result, details = self._is_empty_ai_result(result)
            if is_empty_result:
                raise NullResultError("Operation returned an empty result.", details=details)
            return self._success_outcome(decision, result)
        except Exception as exc:
            return self._failure_outcome(decision, exc)


def _is_empty_value(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False
