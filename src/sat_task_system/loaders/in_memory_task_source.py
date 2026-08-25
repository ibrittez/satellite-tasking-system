from typing import override

from sat_task_system.domain.models import Task
from sat_task_system.ports.task_source import TaskSource


class InMemoryTaskSource(TaskSource):
    """Tasks that were already parsed, held in memory. Nothing to re-read, so
    the list is copied on the way in and on the way out."""

    def __init__(self, tasks: list[Task]) -> None:
        self._tasks: list[Task] = list(tasks)

    @override
    def fetch(self) -> list[Task]:
        return list(self._tasks)
