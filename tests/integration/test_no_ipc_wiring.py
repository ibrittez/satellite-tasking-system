"""Everything except ipc/ and processes/, wired together in one process.

The unit tests cover each piece on its own; this one covers the seams between
them. Task outcomes are hardcoded, so the failure simulation is not under test
here -- that belongs to Satellite.
"""

from pathlib import Path

from sat_task_system.domain.allocator import allocate
from sat_task_system.domain.models import Assignment, TaskResult
from sat_task_system.domain.summary import build_summary
from sat_task_system.loaders.json_task_source import JsonTaskSource
from sat_task_system.reporting.console_reporter import ConsoleReporter
from sat_task_system.reporting.text_report import render_summary

SAT_COUNT = 2
FAILING = {"high_res_capture"}


def execute(assignment: Assignment) -> list[TaskResult]:
    """Stand-in for Satellite.run(): one result per task in the queue."""
    return [
        TaskResult(task.name, assignment.satellite_id, task.name not in FAILING)
        for task in assignment.tasks
    ]


def test_full_chain_without_ipc(spec_tasks_json: Path):
    """Source, allocator, summary and reporter fit together on the spec input."""
    tasks = JsonTaskSource(path=str(spec_tasks_json)).fetch()
    _, assignments = allocate(tasks, sat_count=SAT_COUNT)

    results = [
        result for assignment in assignments for result in execute(assignment)
    ]
    summary = build_summary(tasks, assignments, results)

    reporter = ConsoleReporter()
    reporter.publish(summary)  # visible with `make integration` (pytest -s)

    assert summary.planned_payoff == 16.0
    assert summary.achieved_payoff == 6.0
    assert [task.name for task in summary.skipped] == ["fsck_disk_a"]

    # Every task reaches the report, the skipped one included.
    report = render_summary(summary)
    for task in tasks:
        assert task.name in report
