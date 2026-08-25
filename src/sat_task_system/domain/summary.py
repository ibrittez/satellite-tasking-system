from sat_task_system.domain.models import Assignment, Summary, Task, TaskResult


def build_summary(tasks: list[Task], assignments: list[Assignment], results: list[TaskResult],) -> Summary:
    dispatched = sum(len(assignment.tasks) for assignment in assignments)
    if len(results) != dispatched:
        raise ValueError(
            f"expected one result per dispatched task: "
            f"{dispatched} dispatched, {len(results)} reported."
        )

    assigned_names = {
        task.name for assignment in assignments for task in assignment.tasks
    }

    skipped = tuple(task for task in tasks if task.name not in assigned_names)

    return Summary(tuple(assignments), tuple(results), skipped)
