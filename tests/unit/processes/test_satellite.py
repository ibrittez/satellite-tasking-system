import queue

from sat_task_system.domain.models import Assignment, Task, TaskResult
from sat_task_system.ipc.messages import ExecuteTasks, TaskExecuted
from sat_task_system.processes.satellite import Satellite

SATELLITE_ID = 1


def serve_batch(tasks: tuple[Task, ...], failure_rate: float) -> list[TaskResult]:
    """Run one batch through a Satellite wired to plain queues, no process spawned."""
    inbox: queue.Queue[ExecuteTasks] = queue.Queue()
    outbox: queue.Queue[TaskExecuted] = queue.Queue()
    inbox.put(ExecuteTasks(Assignment(SATELLITE_ID, tasks)))

    Satellite(SATELLITE_ID, failure_rate, inbox, outbox).run()

    return [outbox.get_nowait().result for _ in range(outbox.qsize())]


def test_every_task_in_the_batch_is_reported_once_and_in_order(spec_tasks: list[Task]):
    """One result per assigned task, tagged with the satellite that ran it."""
    _, maintenance, comms, _ = spec_tasks

    results = serve_batch((maintenance, comms), failure_rate=0.0)

    assert [result.task_name for result in results] == [maintenance.name, comms.name]
    assert all(result.satellite_id == SATELLITE_ID for result in results)


def test_a_healthy_satellite_completes_everything(spec_tasks: list[Task]):
    """With a zero failure rate every task succeeds, no seed involved."""
    _, maintenance, comms, _ = spec_tasks

    results = serve_batch((maintenance, comms), failure_rate=0.0)

    assert all(result.success for result in results)


def test_a_broken_satellite_still_reports_its_failures(spec_tasks: list[Task]):
    """With a failure rate of 1.0 every task fails, and none goes unreported."""
    _, maintenance, comms, _ = spec_tasks

    results = serve_batch((maintenance, comms), failure_rate=1.0)

    assert len(results) == 2
    assert not any(result.success for result in results)


def test_the_satellite_returns_after_a_single_batch(spec_tasks: list[Task]):
    """run() serves one ExecuteTasks and returns; a second one is left untouched."""
    capture, maintenance, comms, _ = spec_tasks
    inbox: queue.Queue[ExecuteTasks] = queue.Queue()
    outbox: queue.Queue[TaskExecuted] = queue.Queue()
    inbox.put(ExecuteTasks(Assignment(SATELLITE_ID, (maintenance, comms))))
    inbox.put(ExecuteTasks(Assignment(SATELLITE_ID, (capture,))))

    Satellite(SATELLITE_ID, 0.0, inbox, outbox).run()

    assert outbox.qsize() == 2
    assert inbox.qsize() == 1
