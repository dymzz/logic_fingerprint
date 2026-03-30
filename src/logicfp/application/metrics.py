from dataclasses import dataclass, asdict, field

@dataclass(slots=True)
class InMemoryMetrics:
    total_requests: int = 0
    blocked_requests: int = 0
    probe_requests: int = 0
    success_requests: int = 0
    failed_requests: int = 0
    failed_by_code: dict[str, int] = field(default_factory=dict)
    failed_by_stage: dict[str, int] = field(default_factory=dict)
    failed_by_source: dict[str, int] = field(default_factory=dict)
    failed_by_action: dict[str, int] = field(default_factory=dict)
    failed_by_disposition: dict[str, int] = field(default_factory=dict)
    failed_by_ai_code: dict[str, int] = field(default_factory=dict)
    blocked_by_code: dict[str, int] = field(default_factory=dict)
    blocked_by_stage: dict[str, int] = field(default_factory=dict)
    blocked_by_source: dict[str, int] = field(default_factory=dict)
    blocked_by_action: dict[str, int] = field(default_factory=dict)
    blocked_by_disposition: dict[str, int] = field(default_factory=dict)
    blocked_by_ai_code: dict[str, int] = field(default_factory=dict)
    def record_total(self): self.total_requests += 1
    def record_blocked(self, error_code=None, error_details=None):
        self.blocked_requests += 1
        self._record_dimensions(
            prefix="blocked",
            error_code=error_code,
            error_details=error_details,
        )
    def record_probe(self): self.probe_requests += 1
    def record_success(self): self.success_requests += 1
    def record_failure(self, error_code=None, error_details=None):
        self.failed_requests += 1
        self._record_dimensions(
            prefix="failed",
            error_code=error_code,
            error_details=error_details,
        )
    def snapshot(self): return asdict(self)

    def _record_dimensions(self, *, prefix: str, error_code=None, error_details=None):
        details = error_details if isinstance(error_details, dict) else {}
        fact = details.get("error_fact") if isinstance(details.get("error_fact"), dict) else {}
        policy = details.get("error_policy") if isinstance(details.get("error_policy"), dict) else {}
        ai_error = details.get("ai_error") if isinstance(details.get("ai_error"), dict) else {}

        if error_code:
            self._increment(f"{prefix}_by_code", str(error_code))
        stage = fact.get("stage")
        if stage:
            self._increment(f"{prefix}_by_stage", str(stage))
        source = fact.get("source")
        if source:
            self._increment(f"{prefix}_by_source", str(source))
        action = policy.get("action") or policy.get("disposition")
        if action:
            self._increment(f"{prefix}_by_action", str(action))
            self._increment(f"{prefix}_by_disposition", str(action))
        ai_code = ai_error.get("code")
        if ai_code:
            self._increment(f"{prefix}_by_ai_code", str(ai_code))

    def _increment(self, attr_name: str, key: str):
        bucket = getattr(self, attr_name)
        bucket[key] = bucket.get(key, 0) + 1
