from sat_task_system.domain.models import Task


def allocate(tasks: list[Task]) -> float:
    """Return the maximum payoff achievable by allocating tasks to two groups."""
    memo: dict[tuple[int, frozenset[int], frozenset[int]], float] = {}

    def best(i: int, m1: frozenset[int], m2: frozenset[int]) -> float:
        if i == len(tasks):
            return 0.0

        m_lo, m_hi = sorted((m1, m2), key=sorted)
        key = (i, m_lo, m_hi)
        if key in memo:
            return memo[key]

        t = tasks[i]

        r = best(i+1, m1, m2)

        if not (t.resources & m1):
            r = max(r, t.payoff + best(i + 1, m1 | t.resources, m2))

        if not (t.resources & m2):
            r = max(r, t.payoff + best(i + 1, m1, m2 | t.resources))

        memo[key] = r
        return r

    return best(0, frozenset(), frozenset())
