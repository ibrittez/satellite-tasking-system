import pytest

from sat_task_system.domain.models import Task


def test_resources_normalize_to_frozenset():
    """Task.create should coerce any iterable of ids into a deduplicated frozenset."""
    task1 = Task.create("foo1", 1.0, [1, 5, 1])
    task2 = Task.create("foo2", 1.0, (1, 5))
    task3 = Task.create("foo3", 1.0, {1, 5, 1})
    task4 = Task("foo4", 1.0, frozenset((1, 5, 1)))

    tasks: list[Task] = [task1, task2, task3, task4]

    for task in tasks:
        assert isinstance(task.resources, frozenset)
        assert task.resources == frozenset({1, 5})


def test_resources_is_hashable():
    """resources must be hashable to be usable as part of the DP memo key."""
    task = Task("foo", 10.0, frozenset({1, 5}))
    _ = hash(task.resources)


def test_resources_works_as_part_of_memo_key():
    task = Task.create("foo", 10.0, [1, 5])
    memo: dict[tuple[int, frozenset[int], frozenset[int]], float] = {}
    key = (0, task.resources, frozenset())
    memo[key] = 10.0
    assert memo[key] == 10.0
