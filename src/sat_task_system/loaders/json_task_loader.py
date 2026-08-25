import json

from sat_task_system.domain.models import Task

# =======================================
# public api
# =======================================


def json_task_loader(file_path: str) -> list[Task]:
    """Read a JSON task file and return the tasks it declares."""
    try:
        with open(file_path, "r") as file:
            json_tasks: object = json.load(file)
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Task file not found: {file_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Not a valid JSON document: {file_path}") from error

    return parse_tasks(json_tasks)


def parse_tasks(json_tasks: object) -> list[Task]:
    """Validate already-decoded JSON data and build the tasks. No IO."""
    if not isinstance(json_tasks, list):
        raise ValueError("expected a JSON array of tasks")

    tasks: list[Task] = []
    seen_names: set[str] = set()

    for index, entry in enumerate(json_tasks):
        task: object = entry
        if not isinstance(task, dict):
            raise ValueError(f"task #{index}: expected a JSON object")

        # Re-declare with a known type: isinstance only narrows to dict[Unknown, Unknown].
        fields: dict[str, object] = task

        name = _parse_name(fields, index)
        payoff = _parse_payoff(fields, index)
        resources = _parse_resources(fields, index)

        if name in seen_names:
            raise ValueError(f"task #{index}: duplicated name '{name}'.")
        seen_names.add(name)

        tasks.append(Task.create(name, payoff, resources))

    return tasks


# =======================================
# helpers
# =======================================

def _parse_name(task: dict[str, object], index: int) -> str:
    name = task.get("name")

    if not isinstance(name, str):
        raise ValueError(f"task #{index}: 'name' is missing or not a string.")

    return name


def _parse_payoff(task: dict[str, object], index: int) -> float:
    payoff = task.get("payoff")

    if not isinstance(payoff, (int, float)):
        raise ValueError(
            f"task #{index}: 'payoff' is missing or not a number.")

    return float(payoff)


def _parse_resources(task: dict[str, object], index: int) -> list[int]:
    resources = task.get("resources")

    if not isinstance(resources, list):
        raise ValueError(
            f"task #{index}: 'resources' is missing or not a list.")

    resource_ids: list[int] = []
    for r_index, resource_id in enumerate(resources):
        if not isinstance(resource_id, int):
            raise ValueError(
                f"task #{index}, resource #{r_index} is not an int.")
        resource_ids.append(resource_id)

    return resource_ids
