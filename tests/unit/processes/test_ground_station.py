"""GroundStation phase by phase, plus one pass through run()."""

import queue
from collections.abc import Iterable
from typing import Any, override

from sat_task_system.domain.models import Assignment, Summary, Task, TaskResult
from sat_task_system.ipc.channels import Channels
from sat_task_system.ipc.messages import ExecuteTasks, TaskExecuted
from sat_task_system.ports import Reporter, TaskSource
from sat_task_system.processes.ground_station import GroundStation

# Never reached: every result a test expects is queued before the phase runs.
LONG_TIMEOUT = 1.0

# Long enough to be a real wait, short enough to keep the suite fast.
SILENCE_TIMEOUT = 0.05

# The optimum for spec_tasks, pinned in tests/unit/domain/test_allocator.py:
# payoff 16, with fsck_disk_a left out.
SPEC_BATCHES = [["high_res_capture"], ["sensor_maintenance", "comms_test"]]

CAPTURE_DONE = TaskResult("high_res_capture", 0, True)
MAINTENANCE_DONE = TaskResult("sensor_maintenance", 1, True)
COMMS_DONE = TaskResult("comms_test", 1, True)
COMMS_FAILED = TaskResult("comms_test", 1, False)
ALL_DONE = [CAPTURE_DONE, MAINTENANCE_DONE, COMMS_DONE]


# =======================================
# test doubles
# =======================================


class StubSource(TaskSource):
    """Hands back a list held in memory"""

    def __init__(self, tasks: list[Task]) -> None:
        self._tasks: list[Task] = tasks

    @override
    def fetch(self) -> list[Task]:
        return self._tasks


class CapturingReporter(Reporter):
    """Keeps every summary it is handed instead of printing it."""

    def __init__(self) -> None:
        self.published: list[Summary] = []

    @override
    def publish(self, summary: Summary) -> None:
        self.published.append(summary)


# =======================================
# setup
# =======================================


def local_channels(sat_count: int = 2) -> Channels:
    """Channels backed by queue.Queue: same get/put, no processes"""
    uplinks: Any = tuple(queue.Queue() for _ in range(sat_count))
    downlink: Any = queue.Queue()
    return Channels(uplinks, downlink)


def make_station(
    tasks: list[Task],
    channels: Channels,
    reporter: Reporter | None = None,
    *,
    timeout: float = LONG_TIMEOUT,
) -> GroundStation:
    return GroundStation(
        source=StubSource(tasks),
        reporter=reporter or CapturingReporter(),
        collect_timeout=timeout,
        channels=channels,
        sat_count=len(channels.uplinks),
    )


def spec_plan(tasks: list[Task]) -> list[Assignment]:
    """The optimum for spec_tasks, spelled out instead of asked of the allocator."""
    capture, maintenance, comms, _ = tasks
    return [Assignment(0, (capture,)), Assignment(1, (maintenance, comms))]


# =======================================
# helpers
# =======================================


def send_down(channels: Channels, results: Iterable[TaskResult]) -> None:
    """Queue results on the downlink, as the satellites would have."""
    for result in results:
        channels.downlink.put(TaskExecuted(result))


def read_uplinks(channels: Channels) -> list[ExecuteTasks]:
    """Drain every uplink: what dispatch() sent, in satellite id order."""
    return [uplink.get_nowait() for uplink in channels.uplinks]


def task_names(assignments: Iterable[Assignment]) -> list[list[str]]:
    """The batches as plain names, which is what the assertions compare."""
    return [[task.name for task in a.tasks] for a in assignments]


# =======================================
# schedule
# =======================================


def test_schedule_plans_the_optimum(spec_tasks: list[Task]):
    """The fleet gets the payoff-16 split, one Assignment per satellite."""
    station = make_station(spec_tasks, local_channels())

    assignments = station.schedule(spec_tasks)

    assert [a.satellite_id for a in assignments] == [0, 1]
    assert task_names(assignments) == SPEC_BATCHES


def test_schedule_plans_for_the_configured_fleet_size(spec_tasks: list[Task]):
    """sat_count reaches the allocator: three satellites, three assignments."""
    station = make_station(spec_tasks, local_channels(3))

    assignments = station.schedule(spec_tasks)

    assert [a.satellite_id for a in assignments] == [0, 1, 2]


# =======================================
# dispatch
# =======================================


def test_dispatch_sends_each_batch_up_its_own_uplink(spec_tasks: list[Task]):
    """One command per uplink, carrying that satellite's batch."""
    channels = local_channels()
    station = make_station(spec_tasks, channels)

    station.dispatch(spec_plan(spec_tasks))

    sent = read_uplinks(channels)
    assert [command.assignment.satellite_id for command in sent] == [0, 1]
    assert task_names(command.assignment for command in sent) == SPEC_BATCHES
    assert all(uplink.empty() for uplink in channels.uplinks)


def test_dispatch_addresses_a_satellite_with_nothing_to_do(spec_tasks: list[Task]):
    """An empty batch is still sent: it is what lets that satellite exit."""
    capture, _, comms, _ = spec_tasks
    plan = [Assignment(0, (capture,)), Assignment(
        1, (comms,)), Assignment(2, ())]
    channels = local_channels(3)
    station = make_station(spec_tasks, channels)

    station.dispatch(plan)

    sent = read_uplinks(channels)
    assert task_names(command.assignment for command in sent) == [
        ["high_res_capture"], ["comms_test"], [],
    ]


# =======================================
# collect
# =======================================


def test_collect_stops_at_the_planned_count(spec_tasks: list[Task]):
    """A result nobody planned for is left on the downlink, not drained."""
    channels = local_channels()
    station = make_station(spec_tasks, channels)
    send_down(channels, [*ALL_DONE, TaskResult("fsck_disk_a", 0, True)])

    assert station.collect(spec_plan(spec_tasks)) == ALL_DONE
    assert not channels.downlink.empty()


def test_collect_keeps_arrival_order(spec_tasks: list[Task]):
    """The downlink is shared, so its order need not match the plan's."""
    channels = local_channels()
    station = make_station(spec_tasks, channels)
    arrived = [COMMS_DONE, CAPTURE_DONE, MAINTENANCE_DONE]
    send_down(channels, arrived)

    assert station.collect(spec_plan(spec_tasks)) == arrived


def test_collect_completes_a_missing_result_as_a_failure(spec_tasks: list[Task]):
    """On silence the gap is filled, tagged with the satellite that owed it."""
    channels = local_channels()
    station = make_station(spec_tasks, channels, timeout=SILENCE_TIMEOUT)
    send_down(channels, [CAPTURE_DONE, MAINTENANCE_DONE])

    results = station.collect(spec_plan(spec_tasks))

    assert results == [CAPTURE_DONE, MAINTENANCE_DONE, COMMS_FAILED]


def test_collect_never_duplicates_a_result_that_did_arrive(spec_tasks: list[Task]):
    """Filling the gap is a set difference, so nothing is reported twice."""
    channels = local_channels()
    station = make_station(spec_tasks, channels, timeout=SILENCE_TIMEOUT)
    send_down(channels, [CAPTURE_DONE, MAINTENANCE_DONE])

    results = station.collect(spec_plan(spec_tasks))

    names = [result.task_name for result in results]
    assert len(names) == len(set(names))


def test_collect_fails_every_task_when_the_fleet_stays_silent(spec_tasks: list[Task]):
    """Not one message: still one result per dispatched task, all failed."""
    station = make_station(
        spec_tasks, local_channels(), timeout=SILENCE_TIMEOUT)

    results = station.collect(spec_plan(spec_tasks))

    assert set(results) == {
        TaskResult("high_res_capture", 0, False),
        TaskResult("sensor_maintenance", 1, False),
        COMMS_FAILED,
    }


# =======================================
# report
# =======================================


def test_report_publishes_planned_achieved_and_skipped(spec_tasks: list[Task]):
    """One publish, holding the optimum, what succeeded and what no one took."""
    reporter = CapturingReporter()
    station = make_station(spec_tasks, local_channels(), reporter)

    station.report(
        spec_tasks,
        spec_plan(spec_tasks),
        [CAPTURE_DONE, MAINTENANCE_DONE, COMMS_FAILED],
    )

    assert len(reporter.published) == 1
    summary = reporter.published[0]
    assert summary.planned_payoff == 16.0
    assert summary.achieved_payoff == 11.0
    assert [task.name for task in summary.skipped] == ["fsck_disk_a"]


# =======================================
# run
# =======================================


def test_run_walks_the_five_phases(spec_tasks: list[Task]):
    """End to end: the plan goes out the uplinks and the report comes back."""
    channels = local_channels()
    reporter = CapturingReporter()
    station = make_station(spec_tasks, channels, reporter)

    send_down(channels, ALL_DONE)

    station.run()

    sent = read_uplinks(channels)
    assert task_names(command.assignment for command in sent) == SPEC_BATCHES
    assert reporter.published[0].achieved_payoff == 16.0
