from typing import override

from sat_task_system.domain.models import Summary, Task
from sat_task_system.ports.reporter import Reporter

MARK_WIDTH = 7
NAME_WIDTH = 26
PAYOFF_WIDTH = 7
RESOURCE_GAP = 3

OK_MARK: str = "OK"
FAIL_MARK: str = "FAIL"

# Same widths as _row, so the header cannot drift from the columns it names.
COLUMNS = (f"  {'':<{MARK_WIDTH}}{'':<{NAME_WIDTH}}"
           f"{'payoff':>{PAYOFF_WIDTH}}{'':<{RESOURCE_GAP}}resources")


class ConsoleReporter(Reporter):
    @override
    def publish(self, summary: Summary) -> None:
        # One write, so a concurrent process cannot interleave into the report.
        print(self.render(summary))

    def render(self, summary: Summary) -> str:
        """The whole report as one string. No IO, so it is testable directly."""
        outcomes = {
            result.task_name: result.success for result in summary.results}

        assigned = sum(len(assignment.tasks)
                       for assignment in summary.assignments)
        skipped = len(summary.skipped)
        succeeded = sum(1 for result in summary.results if result.success)

        lines: list[str] = [
            f"{assigned + skipped} tasks, {assigned} assigned across "
            f"{len(summary.assignments)} satellites, {skipped} skipped",
            "",
            COLUMNS,
        ]

        for assignment in summary.assignments:
            lines.append(f"satellite {assignment.satellite_id}:")
            for task in assignment.tasks:
                mark = "["+OK_MARK+"]" if outcomes[task.name] else "["+FAIL_MARK+"]"
                lines.append(self._row(mark, task))

        if summary.skipped:
            lines.append("\nskipped:")
            lines.extend(self._row("", task) for task in summary.skipped)

        lines.append(f"\nplanned {summary.planned_payoff:.1f}"
                     f"   achieved {summary.achieved_payoff:.1f}"
                     f"   ({succeeded} of {len(summary.results)} succeeded)")

        return "\n".join(lines)

    @staticmethod
    def _row(mark: str, task: Task) -> str:
        """One task line: marker, name, payoff, and the resources it claims."""
        # Sorted, because frozenset iteration order is not guaranteed.
        resources = ", ".join(str(resource)
                              for resource in sorted(task.resources))

        return (f"  {mark:<{MARK_WIDTH}}"
                f"{task.name:<{NAME_WIDTH}}"
                f"{task.payoff:>{PAYOFF_WIDTH}.1f}"
                f"{'':<{RESOURCE_GAP}}" + "{" + resources + "}")
