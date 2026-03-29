from dataclasses import dataclass

from .domain.executor import LogicFingerprintExecutor
from .domain.fsm import LogicFingerprintFSM


@dataclass(slots=True)
class LogicFingerprintService:
    fsm: LogicFingerprintFSM

    def build_executor(self) -> LogicFingerprintExecutor:
        return LogicFingerprintExecutor(self.fsm)


