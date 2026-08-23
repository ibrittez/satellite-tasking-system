from pathlib import Path

import pytest

from sat_task_system.domain.models import Task
from sat_task_system.loaders.json_task_source import JsonTaskSource


def test_spec_task_loaded_properly(spec_tasks: list[Task], spec_tasks_json: Path):
    """The spec JSON file round-trips into the same Task objects the domain tests use."""
    tasks = JsonTaskSource(str(spec_tasks_json)).fetch()
    assert tasks == spec_tasks
