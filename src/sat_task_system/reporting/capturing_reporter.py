from typing import override

from sat_task_system.domain.models import Summary
from sat_task_system.ports.reporter import Reporter


class CapturingReporter(Reporter):
    """Keeps the summary instead of emitting it, for a caller that runs the
    station in its own process and needs the outcome back in memory."""

    def __init__(self) -> None:
        self._summary: Summary | None = None

    @override
    def publish(self, summary: Summary) -> None:
        self._summary = summary

    @property
    def summary(self) -> Summary:
        """The published summary. Raises if the run never reached its report."""
        if self._summary is None:
            raise RuntimeError("no run has been published yet")

        return self._summary
