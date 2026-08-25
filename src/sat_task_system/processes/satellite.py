from multiprocessing.queues import Queue
import random
import time

from sat_task_system.domain.models import Task, TaskResult
from sat_task_system.ipc.messages import ExecuteTasks, TaskExecuted

EXECUTION_SECONDS = 0.05


class MisroutedCommandError(ValueError):
    """A command reached a satellite it was not addressed to."""


class Satellite:
    def __init__(self, sat_id: int,
                 failure_rate: float,
                 uplink: Queue[ExecuteTasks],
                 downlink: Queue[TaskExecuted]) -> None:
        self._sat_id: int = sat_id
        self._failure_rate: float = failure_rate
        self._uplink: Queue[ExecuteTasks] = uplink
        self._downlink: Queue[TaskExecuted] = downlink
        self._rng: random.Random = random.Random()

    def run(self) -> None:
        """Wait for one batch, execute it in order, report each task exactly once."""
        command = self._uplink.get()

        received_id = command.assignment.satellite_id
        if received_id != self._sat_id:
            raise MisroutedCommandError(
                f"satellite {self._sat_id}: got a command addressed to " +
                f"satellite {received_id}."
            )

        for task in command.assignment.tasks:
            result = TaskResult(task.name, self._sat_id, self._execute())
            self._downlink.put(TaskExecuted(result))

    def _execute(self) -> bool:
        """Simulated run: takes a moment, and fails with probability failure_rate."""
        time.sleep(EXECUTION_SECONDS)
        return self._rng.random() >= self._failure_rate
