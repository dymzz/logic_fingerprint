from dataclasses import dataclass, field


@dataclass(slots=True)
class PolicyConfig:
    error_strategies: dict[str, str] = field(default_factory=lambda: {
        "ERR_TIMEOUT": "retry_once",
        "ERR_VALIDATION": "fail_fast",
        "ERR_LOGIC": "fail_fast",
        "ERR_UNKNOWN": "fail_fast",
    })