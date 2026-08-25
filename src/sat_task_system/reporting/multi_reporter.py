from collections.abc import Sequence
from typing import override

from sat_task_system.domain.models import Summary
from sat_task_system.ports.reporter import Reporter


class MultiReporter(Reporter):
    """Forwards one summary to several reporters, in order."""

    def __init__(self, reporters: Sequence[Reporter]) -> None:
        self._reporters: tuple[Reporter, ...] = tuple(reporters)

    @override
    def publish(self, summary: Summary) -> None:
        for reporter in self._reporters:
            reporter.publish(summary)
