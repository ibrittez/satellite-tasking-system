import pytest

from sat_task_system.domain.models import Assignment, Task, TaskResult, Summary
from sat_task_system.domain.summary import build_summary


def result(task: Task, satellite_id: int, success: bool) -> TaskResult:
    """Build the TaskResult a satellite would report for `task`."""
    return TaskResult(task.name, satellite_id, success)


def test_summary_reports_planned_achieved_and_skipped(spec_tasks: list[Task]):
    """On the spec plan with one failed task: 16 planned, 6 achieved, fsck_disk_a skipped."""
    capture, maintenance, comms, fsck = spec_tasks
    assignments = [
        Assignment(satellite_id=0, tasks=(capture,)),
        Assignment(satellite_id=1, tasks=(maintenance, comms)),
    ]

    results = [
        result(maintenance, 1, success=True),
        result(capture, 0, success=False),
        result(comms, 1, success=True),
    ]

    summary = build_summary(spec_tasks, assignments, results)

    assert summary.planned_payoff == 16.0
    assert summary.achieved_payoff == 6.0
    assert summary.skipped == (fsck,)


def test_missing_result_is_rejected(spec_tasks: list[Task]):
    """A lost report must raise, not read as a task that failed."""
    capture, maintenance, comms, _ = spec_tasks
    assignments = [
        Assignment(satellite_id=0, tasks=(capture,)),
        Assignment(satellite_id=1, tasks=(maintenance, comms)),
    ]
    results = [result(capture, 0, success=True)]

    with pytest.raises(ValueError):
        _ = build_summary(spec_tasks, assignments, results)
