from typing import override

from sat_task_system.domain.models import Task
from sat_task_system.loaders.json_task_loader import json_task_loader
from sat_task_system.ports import TaskSource


class JsonTaskSource(TaskSource):
    def __init__(self, path: str) -> None:
        self._path: str = path

    @override
    def fetch(self) -> list[Task]:
        return json_task_loader(self._path)
