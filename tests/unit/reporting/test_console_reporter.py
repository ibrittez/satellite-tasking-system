from sat_task_system.domain.models import Assignment, Summary, Task, TaskResult
from sat_task_system.reporting.console_reporter import ConsoleReporter

# Update these two if the success/failure markers change.
OK_MARK = "OK"
FAIL_MARK = "FAIL"


def line_with(report: str, needle: str) -> str:
    """The one report line mentioning `needle`, so assertions ignore spacing."""
    matches = [line for line in report.splitlines() if needle in line]
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


def clean_summary(spec_tasks: list[Task]) -> Summary:
    """A run where every loaded task got assigned, so nothing is skipped."""
    capture, maintenance, *_ = spec_tasks
    return Summary(
        assignments=(
            Assignment(satellite_id=0, tasks=(capture,)),
            Assignment(satellite_id=1, tasks=(maintenance,)),
        ),
        results=(
            TaskResult(capture.name, 0, success=True),
            TaskResult(maintenance.name, 1, success=True),
        ),
        skipped=(),
    )


def test_every_dispatched_task_is_listed_with_its_outcome(spec_tasks: list[Task]):
    """Each assigned task gets its own line, flagged by whether it succeeded."""
    capture, maintenance, comms, _ = spec_tasks

    report = ConsoleReporter().render(spec_summary(spec_tasks))

    assert FAIL_MARK in line_with(report, capture.name)
    assert OK_MARK in line_with(report, maintenance.name)
    assert OK_MARK in line_with(report, comms.name)


def test_skipped_tasks_and_payoff_totals_are_reported(spec_tasks: list[Task]):
    """The report shows what no satellite could take, and planned next to achieved."""
    *_, fsck = spec_tasks

    report = ConsoleReporter().render(spec_summary(spec_tasks))

    assert fsck.name in report
    # Compared as whitespace-split tokens: "6.0" is a substring of "16.0".
    totals = line_with(report, "planned").split()
    assert "16.0" in totals
    assert "6.0" in totals


def test_each_task_row_shows_the_resources_it_claims(spec_tasks: list[Task]):
    """Resources travel next to their task -- that is what makes the plan
    verifiable by eye, and why fsck_disk_a fits nowhere."""
    capture, _, _, fsck = spec_tasks

    report = ConsoleReporter().render(spec_summary(spec_tasks))

    assert "{1, 5}" in line_with(report, capture.name)
    assert "{1, 6}" in line_with(report, fsck.name)
    # A bare number is a guess, so both columns are named.
    assert "payoff" in line_with(report, "resources")


def test_resource_ids_are_listed_in_ascending_order():
    """Sorted, not in set order: a report that reshuffles between runs is not
    trusted, and frozenset iteration order is not guaranteed."""
    scan = Task.create("wide_scan", 3.0, (8, 1))
    summary = Summary(
        assignments=(Assignment(satellite_id=0, tasks=(scan,)),),
        results=(TaskResult(scan.name, 0, success=True),),
        skipped=(),
    )

    report = ConsoleReporter().render(summary)

    assert "{1, 8}" in line_with(report, scan.name)


def test_the_counts_line_splits_the_loaded_task_list(spec_tasks: list[Task]):
    """Assigned and skipped are reported against the total, so 1 skipped of 4
    reads as a proportion instead of as a lone section."""
    report = ConsoleReporter().render(spec_summary(spec_tasks))

    counts = line_with(report, "assigned")
    assert "4 tasks" in counts
    assert "3 assigned" in counts
    assert "2 satellites" in counts
    assert "1 skipped" in counts


def test_the_totals_line_reports_how_many_tasks_succeeded(spec_tasks: list[Task]):
    """The failure count is what explains a gap between planned and achieved."""
    report = ConsoleReporter().render(spec_summary(spec_tasks))

    assert "2 of 3" in line_with(report, "planned")


def test_the_skipped_section_is_omitted_when_nothing_was_skipped(
        spec_tasks: list[Task]):
    """No empty heading: the section only appears when it has rows to show.
    Matched on the heading, since the counts line still says `0 skipped`."""
    report = ConsoleReporter().render(clean_summary(spec_tasks))

    assert "skipped:" not in report
    assert "0 skipped" in line_with(report, "assigned")
