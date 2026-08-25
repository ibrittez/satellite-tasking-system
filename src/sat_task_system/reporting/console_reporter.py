from typing import override

from sat_task_system.domain.models import Summary
from sat_task_system.ports.reporter import Reporter
from sat_task_system.reporting.text_report import render_summary


class ConsoleReporter(Reporter):
    """Writes the run to stdout. The layout itself lives in text_report."""

    @override
    def publish(self, summary: Summary) -> None:
        # One write, so a concurrent process cannot interleave into the report.
        print(render_summary(summary))
