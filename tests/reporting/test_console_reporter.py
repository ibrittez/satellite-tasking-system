import pytest

from sat_task_system.domain.models import Assignment, Summary, Task, TaskResult
from sat_task_system.reporting.console_reporter import ConsoleReporter, OK_MARK, FAIL_MARK


def line_with(output: str, needle: str) -> str:
    """The one output line mentioning `needle`, so assertions ignore spacing."""
    matches = [line for line in output.splitlines() if needle in line]
    assert len(
        matches) == 1, f"expected one line for {needle!r}, got {matches}"
    return matches[0]


def spec_summary(spec_tasks: list[Task]) -> Summary:
    """The spec plan on two satellites, with high_res_capture failing."""
    capture, maintenance, comms, fsck = spec_tasks
    return Summary(
        assignments=(
            Assignment(satellite_id=0, tasks=(capture,)),
            Assignment(satellite_id=1, tasks=(maintenance, comms)),
        ),
        results=(
            TaskResult(capture.name, 0, success=False),
            TaskResult(maintenance.name, 1, success=True),
            TaskResult(comms.name, 1, success=True),
        ),
        skipped=(fsck,),
    )


def test_every_dispatched_task_is_listed_with_its_outcome(
    spec_tasks: list[Task], capsys: pytest.CaptureFixture[str]
):
    """Each assigned task gets its own line, flagged by whether it succeeded."""
    capture, maintenance, comms, _ = spec_tasks

    ConsoleReporter().publish(spec_summary(spec_tasks))
    out = capsys.readouterr().out

    assert FAIL_MARK in line_with(out, capture.name)
    assert OK_MARK in line_with(out, maintenance.name)
    assert OK_MARK in line_with(out, comms.name)


def test_skipped_tasks_and_payoff_totals_are_reported(
    spec_tasks: list[Task], capsys: pytest.CaptureFixture[str]
):
    """The report shows what no satellite could take, and planned next to achieved."""
    *_, fsck = spec_tasks

    ConsoleReporter().publish(spec_summary(spec_tasks))
    out = capsys.readouterr().out

    assert fsck.name in out
    # Compared as whitespace-split tokens: "6.0" is a substring of "16.0".
    totals = line_with(out, "planned").split()
    assert "16.0" in totals
    assert "6.0" in totals
