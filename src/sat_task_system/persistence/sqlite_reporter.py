from typing import override

from sat_task_system.domain.models import Summary
from sat_task_system.persistence.sqlite_store import SqliteStore
from sat_task_system.ports.reporter import Reporter


class SqliteReporter(Reporter):
    """Records the run instead of showing it. `publish()` is terminal and called
    once, which maps onto exactly one transaction in the store."""

    def __init__(self, db_path: str) -> None:
        self._store: SqliteStore = SqliteStore(db_path)

    @override
    def publish(self, summary: Summary) -> None:
        _ = self._store.save(summary)
