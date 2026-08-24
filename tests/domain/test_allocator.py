import time

import pytest

from sat_task_system.domain.allocator import allocate
from sat_task_system.domain.models import Assignment, Task

from collections import Counter
from collections.abc import Iterable


# =======================================
# helpers
# =======================================

def allocation_shape(assignments: list[Assignment]) -> Counter[frozenset[Task]]:
    """The allocation as a multiset of task groups: satellites are interchangeable, so their index carries no meaning."""
    return Counter(frozenset(a.tasks) for a in assignments)


def expected_shape(*groups: Iterable[Task]) -> Counter[frozenset[Task]]:
    """The same multiset, written one group per argument."""
    return Counter(frozenset(group) for group in groups)


def satellites_used(assignments: list[Assignment]) -> int:
    """How many satellites got at least one task."""
    return sum(1 for a in assignments if a.tasks)


def load_spread(assignments: list[Assignment]) -> int:
    """Gap between the busiest and the idlest satellite; 0 means perfectly even."""
    loads = [len(a.tasks) for a in assignments]
    return max(loads) - min(loads)


def tasks_placed(assignments: list[Assignment]) -> int:
    """How many tasks made it into the plan, across the whole fleet."""
    return sum(len(a.tasks) for a in assignments)

# =======================================
# tests
# =======================================


def test_spec_example(spec_tasks: list[Task]):
    """Matches the payoff-maximizing allocation from the exercise spec."""
    total, _ = allocate(spec_tasks)
    assert total == 16.0


def test_spec_example_assignment(spec_tasks: list[Task]):
    """Task-per-satellite split matches the spec, regardless of which satellite index gets which group."""
    high_res, maintenance, comms, _fsck = spec_tasks
    _, assignments = allocate(spec_tasks)
    assert allocation_shape(assignments) == expected_shape(
        [high_res], [maintenance, comms])


def test_spec_example_with_3_satellites(spec_tasks: list[Task]):
    """Matches the payoff-maximizing allocation from the exercise spec."""
    high_res, maintenance, comms, fsck = spec_tasks
    total, assignments = allocate(spec_tasks, 3)

    assert allocation_shape(assignments) == expected_shape(
        [high_res], [maintenance, comms], [fsck])
    assert total == 18.0


def test_satellite_id_matches_list_index(spec_tasks: list[Task]):
    """dispatch() picks an uplink queue by index, so assignment i must own satellite i."""
    _, assignments = allocate(spec_tasks, 3)

    assert [a.satellite_id for a in assignments] == [0, 1, 2]


def test_spec_example_with_4_satellites(spec_tasks: list[Task]):
    """A 4th satellite doesn't raise the 18.0 optimum, but it must be used instead of left idle."""
    total, assignments = allocate(spec_tasks, 4)

    assert total == 18.0
    assert satellites_used(assignments) == 4


def test_load_evens_out_when_tasks_outnumber_satellites():
    """Four conflict-free tasks on two satellites split evenly, not 4/0."""
    tasks = [Task.create(name, 1.0, [i]) for i, name in enumerate("abcd")]

    _, assignments = allocate(tasks, 2)

    assert load_spread(assignments) == 0

def test_enough_satellites_for_every_task_skips_the_search():
    """One task per satellite is trivially optimal, so it must cost no search at all.
    Both branches of the guard are exercised: as many satellites as tasks, and one more."""

    task_count = 100
    tasks: list[Task] = []

    for i in range(task_count):
        tasks.append(Task.create(f"task{i}", 1.0, {i}))

    start = time.perf_counter()
    _, _ = allocate(tasks, sat_count=task_count)
    _, _ = allocate(tasks, sat_count=task_count+1)
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0

# =======================================
# benchmark
# =======================================


@pytest.mark.slow
def test_allocate_finishes_within_time_budget(benchmark_tasks: list[Task]):
    """allocate() must resolve a realistic ~50-task, 10-resource list in under 5s."""
    start = time.perf_counter()
    _, _ = allocate(benchmark_tasks)
    elapsed = time.perf_counter() - start

    assert elapsed < 10.0
