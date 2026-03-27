from dataclasses import dataclass

from .executor import LogicFingerprintExecutor
from .fsm import LogicFingerprintFSM


@dataclass(slots=True)
class LogicFingerprintService:
    fsm: LogicFingerprintFSM

    def build_executor(self) -> LogicFingerprintExecutor:
        return LogicFingerprintExecutor(self.fsm)
