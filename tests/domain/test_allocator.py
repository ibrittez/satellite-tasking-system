import time

from sat_task_system.domain.allocator import allocate
from sat_task_system.domain.models import Task


def test_spec_example(spec_tasks: list[Task]):
    """Matches the payoff-maximizing allocation from the exercise spec."""
    total, _ = allocate(spec_tasks)
    assert total == 16.0


def test_allocate_finishes_within_time_budget(benchmark_tasks: list[Task]):
    """allocate() must resolve a realistic ~50-task, 10-resource list in under 5s."""
    start = time.perf_counter()
    _, _ = allocate(benchmark_tasks)
    elapsed = time.perf_counter() - start

    assert elapsed < 5.0 
