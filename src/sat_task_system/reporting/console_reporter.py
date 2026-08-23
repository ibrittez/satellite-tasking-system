from typing import override

from sat_task_system.domain.models import Summary, Task
from sat_task_system.ports import Reporter

MARK_WIDTH = 7
NAME_WIDTH = 26
PAYOFF_WIDTH = 7

OK_MARK: str = "OK"
FAIL_MARK: str = "FAIL"


class ConsoleReporter(Reporter):
    @override
    def publish(self, summary: Summary) -> None:
        outcomes = {
            result.task_name: result.success for result in summary.results}

        for assignment in summary.assignments:
            print(f"satellite {assignment.satellite_id}:")
            for task in assignment.tasks:
                mark = "["+OK_MARK+"]" if outcomes[task.name] else "["+FAIL_MARK+"]"
                print(self._row(mark, task))

        print("\nskipped:")
        for task in summary.skipped:
            print(self._row("", task))

        print(f"\nplanned {summary.planned_payoff:.1f}" +
              f"   achieved {summary.achieved_payoff:.1f}")

    @staticmethod
    def _row(mark: str, task: Task) -> str:
        """One task line: marker, then name and payoff in fixed columns."""
        return (f"  {mark:<{MARK_WIDTH}}"
                f"{task.name:<{NAME_WIDTH}}"
                f"{task.payoff:>{PAYOFF_WIDTH}.1f}")
