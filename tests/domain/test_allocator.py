import time

from sat_task_system.domain.allocator import allocate
from sat_task_system.domain.models import Task


def test_spec_example(spec_tasks: list[Task]):
    """Matches the payoff-maximizing allocation from the exercise spec."""
    total, _ = allocate(spec_tasks)
    assert total == 16.0


def test_spec_example_assignment(spec_tasks: list[Task]):
    """Task-per-satellite split matches the spec, regardless of which satellite index gets which group."""
    _, assignments = allocate(spec_tasks)

    expected_names = {
        frozenset({"high_res_capture"}),
        frozenset({"sensor_maintenance", "comms_test"}),
    }

    assert len(assignments) == 2
    assigned_names = frozenset(frozenset(t.name for t in group)
                               for group in assignments)
    assert assigned_names == expected_names


def test_allocate_finishes_within_time_budget(benchmark_tasks: list[Task]):
    """allocate() must resolve a realistic ~50-task, 10-resource list in under 5s."""
    start = time.perf_counter()
    _, _ = allocate(benchmark_tasks)
    elapsed = time.perf_counter() - start

    assert elapsed < 5.0
