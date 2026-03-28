from dataclasses import dataclass


@dataclass(slots=True)
class StrategyConfig:
    default_strategy: str = "fail_fast"

    # retry策略参数（后面会用）
    retry_once_max_attempts: int = 1