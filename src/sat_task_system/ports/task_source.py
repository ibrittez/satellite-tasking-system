"""The port the GroundStation reads its work through."""

from abc import ABC, abstractmethod

from sat_task_system.domain.models import Task


class TaskSource(ABC):
    """Where the tasks of a run come from"""

    @abstractmethod
    def fetch(self) -> list[Task]:
        """The tasks to plan, already parsed into domain objects."""
