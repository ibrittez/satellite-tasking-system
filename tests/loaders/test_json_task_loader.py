from pathlib import Path

import pytest

from sat_task_system.domain.models import Task
from sat_task_system.loaders.json_task_loader import json_task_loader, parse_tasks

# pyright: reportUnusedCallResult=false


def test_spec_task_loaded_properly(spec_tasks: list[Task], spec_tasks_json: Path):
    """The spec JSON file round-trips into the same Task objects the domain tests use."""
    tasks = json_task_loader(str(spec_tasks_json))
    assert tasks == spec_tasks


def test_missing_file_raises(tmp_path: Path):
    """A path that does not exist must raise, not return an empty list."""
    with pytest.raises(FileNotFoundError):
        json_task_loader(str(tmp_path / "does_not_exist.json"))


def test_malformed_json_raises(tmp_path: Path):
    """A file that is not valid JSON must raise, not return an empty list."""
    file_path = tmp_path / "broken.json"
    file_path.write_text("{ this is not json")

    with pytest.raises(ValueError):
        json_task_loader(str(file_path))


def test_top_level_object_instead_of_list_raises():
    """A JSON object at the top level is not a task list and must be rejected."""
    with pytest.raises(ValueError):
        parse_tasks(
            {"tasks": [{"name": "a", "payoff": 1.0, "resources": [1]}]})


def test_missing_required_field_raises():
    """A task entry without 'payoff' must raise a clear error, not a bare KeyError."""
    with pytest.raises(ValueError):
        parse_tasks([{"name": "no_payoff", "resources": [1, 2]}])
    with pytest.raises(ValueError):
        parse_tasks([{"name": "no_resources", "payoff": 1.0}])
    with pytest.raises(ValueError):
        parse_tasks([{"payoff": 1.0, "resources": [1, 2]}])


def test_non_numeric_payoff_raises():
    """A string payoff must be rejected at load time: the allocator compares payoffs."""
    with pytest.raises(ValueError):
        parse_tasks(
            [{"name": "bad_payoff", "payoff": "ten", "resources": [1]}])


def test_non_iterable_resources_raises():
    """A scalar 'resources' must raise a clear error, not a bare TypeError from frozenset()."""
    with pytest.raises(ValueError):
        parse_tasks([{"name": "bad_resources", "payoff": 1.0, "resources": 5}])


def test_non_integer_resource_id_raises():
    """Resource ids must be ints: a string id only explodes later, inside the allocator bitmask."""
    with pytest.raises(ValueError):
        parse_tasks(
            [{"name": "str_resource", "payoff": 1.0, "resources": [1, "5"]}])


def test_duplicate_task_names_raise():
    """Names identify tasks in the final report, so duplicates must be rejected."""
    with pytest.raises(ValueError):
        parse_tasks([
            {"name": "same", "payoff": 1.0, "resources": [1]},
            {"name": "same", "payoff": 2.0, "resources": [2]},
        ])
