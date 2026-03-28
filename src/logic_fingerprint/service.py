from dataclasses import dataclass

from .core.executor import LogicFingerprintExecutor
from .core.fsm import LogicFingerprintFSM


@dataclass(slots=True)
class LogicFingerprintService:
    fsm: LogicFingerprintFSM

    def build_executor(self) -> LogicFingerprintExecutor:
        return LogicFingerprintExecutor(self.fsm)
