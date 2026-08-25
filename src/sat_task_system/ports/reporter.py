"""The port the GroundStation hands its results to."""

from abc import ABC, abstractmethod

from sat_task_system.domain.models import Summary


class Reporter(ABC):
    @abstractmethod
    def publish(self, summary: Summary) -> None:
        """Emit the summary of one finished run."""
