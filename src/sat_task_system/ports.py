"""The ports of a ports-and-adapters design: the abstract edges the
GroundStation depends on, so it never names a file format or an output device.
"""

from abc import ABC, abstractmethod

from sat_task_system.domain.models import Task, Summary


class TaskSource(ABC):
    @abstractmethod
    def fetch(self) -> list[Task]: ...


class Reporter(ABC):
    @abstractmethod
    def publish(self, summary: Summary) -> None: ...
