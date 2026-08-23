from dataclasses import dataclass
from collections.abc import Iterable


class ResourceConflictError(ValueError):
    """An Assignment was built with two tasks claiming the same resource id."""


@dataclass(frozen=True, slots=True)
class Task:
    name: str
    payoff: float
    resources: frozenset[int]

    @classmethod
    def create(cls, name: str, payoff: float, resources: Iterable[int]) -> "Task":
        """Build a Task from any iterable of resource ids (list/tuple/set/frozenset)."""
        return cls(name, payoff, frozenset(resources))


@dataclass(frozen=True, slots=True)
class Assignment:
    """The tasks one satellite is asked to run, guaranteed resource-disjoint."""

    satellite_id: int
    tasks: tuple[Task, ...]

    def __post_init__(self) -> None:
        claimed: set[int] = set()
        for task in self.tasks:
            conflict = claimed & task.resources
            if conflict:
                raise ResourceConflictError(
                    f"satellite {self.satellite_id}: task '{task.name}' claims " +
                    f"resource(s) {sorted(conflict)}, already held by an earlier task."
                )
            claimed |= task.resources

    @property
    def payoff(self) -> float:
        """Payoff this assignment yields if every task succeeds."""
        return sum(task.payoff for task in self.tasks)

