"""Transport envelopes. Payloads are domain types, wrapped for the wire.

Named by kind: a command is imperative and addressed to one recipient, an event
is past tense and a statement of fact.
"""

from dataclasses import dataclass

from sat_task_system.domain.models import Assignment, TaskResult


@dataclass(frozen=True, slots=True)
class ExecuteTasks:
    """Command, station -> satellite: run this batch, in order."""

    assignment: Assignment


@dataclass(frozen=True, slots=True)
class TaskExecuted:
    """Event, satellite -> station: this task was attempted, with this outcome."""

    result: TaskResult
