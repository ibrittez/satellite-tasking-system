from queue import Empty

from sat_task_system.domain.allocator import allocate
from sat_task_system.domain.models import Task, Assignment, TaskResult
from sat_task_system.domain.summary import build_summary
from sat_task_system.ipc.channels import Channels
from sat_task_system.ipc.messages import ExecuteTasks, TaskExecuted
from sat_task_system.ports.reporter import Reporter
from sat_task_system.ports.task_source import TaskSource


class GroundStation:
    def __init__(self,
                 source: TaskSource,
                 reporter: Reporter,
                 collect_timeout: float,
                 channels: Channels,
                 sat_count: int = 2
                 ) -> None:
        self._source: TaskSource = source
        self._reporter: Reporter = reporter
        self._sat_count: int = sat_count
        self._collect_timeout: float = collect_timeout
        self._channels: Channels = channels

    def run(self) -> None:
        tasks = self._source.fetch()
        assignments = self.schedule(tasks)
        self.dispatch(assignments)
        results = self.collect(assignments)
        self.report(tasks, assignments, results)

    def schedule(self, tasks: list[Task]) -> list[Assignment]:
        _, asig = allocate(tasks, self._sat_count)
        return asig

    def dispatch(self, assignments: list[Assignment]) -> None:
        for a in assignments:
            self._channels.uplinks[a.satellite_id].put(ExecuteTasks(a))

    def collect(self, assignments: list[Assignment]) -> list[TaskResult]:
        task_count = sum(len(a.tasks) for a in assignments)

        results: list[TaskResult] = []
        for _ in range(task_count):
            try:
                message: TaskExecuted = self._channels.downlink.get(
                    timeout=self._collect_timeout)
            except Empty:
                break
            results.append(message.result)

        received = {
            (result.satellite_id, result.task_name)
            for result in results
        }

        expected = {
            (a.satellite_id, task.name)
            for a in assignments
            for task in a.tasks
        }

        for sat_id, task_name in expected - received:
            results.append(TaskResult(task_name, sat_id, False))

        return results

    def report(self,
               tasks: list[Task],
               assignments: list[Assignment],
               results: list[TaskResult]
               ) -> None:
        summary = build_summary(tasks, assignments, results)
        self._reporter.publish(summary)
