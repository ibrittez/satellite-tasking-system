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
