from sat_task_system.domain.allocator import allocate
from sat_task_system.domain.models import Task, Assignment, TaskResult
from sat_task_system.domain.summary import build_summary
from sat_task_system.ports import Reporter, TaskSource


class GroundStation:
    def __init__(self, source: TaskSource, reporter: Reporter,
                 sat_count: int = 2) -> None:
        self._source: TaskSource = source
        self._reporter: Reporter = reporter
        self._sat_count: int = sat_count
        self._assignments: list[Assignment] = []

    def run(self) -> None:
        tasks = self._source.fetch()
        self._assignments = self.schedule(tasks)
        self.dispatch()
        results = self.collect()
        self.report(tasks, results)

    def schedule(self, tasks: list[Task]) -> list[Assignment]:
        _, asig = allocate(tasks, self._sat_count)
        return asig

    def dispatch(self) -> None:
        raise NotImplementedError

    def collect(self) -> list[TaskResult]:
        raise NotImplementedError

    def report(self, tasks: list[Task], results: list[TaskResult]) -> None:
        summary = build_summary(tasks, self._assignments, results)
        self._reporter.publish(summary)
