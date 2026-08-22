from dataclasses import dataclass
from collections.abc import Iterable


@dataclass(frozen=True, slots=True)
class Task:
    name: str
    payoff: float
    resources: frozenset[int]

    @classmethod
    def create(cls, name: str, payoff: float, resources: Iterable[int]) -> "Task":
        """Build a Task from any iterable of resource ids (list/tuple/set/frozenset)."""
        return cls(name, payoff, frozenset(resources))
