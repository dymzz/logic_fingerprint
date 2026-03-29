class InMemoryConsensusBackend:
    def __init__(self) -> None:
        self._failed_nodes: set[str] = set()
    def mark_failed(self, instance_id: str) -> None:
        self._failed_nodes.add(instance_id)
    def clear_failed(self, instance_id: str) -> None:
        self._failed_nodes.discard(instance_id)
    def fail_count(self) -> int:
        return len(self._failed_nodes)
    def is_failed(self, instance_id: str) -> bool:
        return instance_id in self._failed_nodes
