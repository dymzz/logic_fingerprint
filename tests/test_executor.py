import asyncio

from logic_fingerprint.config import RuntimeConfig
from logic_fingerprint.consensus import InMemoryConsensusBackend
from logic_fingerprint.core.executor import LogicFingerprintExecutor
from logic_fingerprint.core.fsm import LogicFingerprintFSM


def build_executor(**kwargs) -> LogicFingerprintExecutor:
    config = RuntimeConfig(**kwargs)
    backend = InMemoryConsensusBackend()
    fsm = LogicFingerprintFSM(
        instance_id="node-a",
        config=config,
        backend=backend,
    )
    return LogicFingerprintExecutor(fsm)


def test_closed_state_executes_successfully():
    executor = build_executor()
    outcome = executor.execute(lambda: {"ok": True})
    assert outcome.executed is True
    assert outcome.succeeded is True


def test_async_execute_supports_async_handler():
    executor = build_executor()

    async def run():
        return await executor.execute_async(lambda: async_ok())

    async def async_ok():
        return {"async": True}

    outcome = asyncio.run(run())
    assert outcome.executed is True
    assert outcome.succeeded is True
