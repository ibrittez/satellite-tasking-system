from sat_task_system.domain.models import Task


def resources_to_bitmask(resources: frozenset[int]) -> int:
    mask = 0
    for r in resources:
        mask |= 1 << r
    return mask


def allocate(tasks: list[Task]) -> float:
    # memoization storage
    memo: dict[tuple[int, int, int], float] = {}

    # precompute bitmask once
    resources_bitmasks = [resources_to_bitmask(t.resources) for t in tasks]

    def best(i: int, m1: int, m2: int) -> float:
        if i == len(tasks):
            return 0.0

        lo, hi = (m1, m2) if m1 <= m2 else (m2, m1)
        key = (i, lo, hi)
        if key in memo:
            return memo[key]

        t_mask = resources_bitmasks[i]
        r = best(i + 1, m1, m2)
        if not (t_mask & m1):
            r = max(r, tasks[i].payoff + best(i + 1, m1 | t_mask, m2))
        if not (t_mask & m2):
            r = max(r, tasks[i].payoff + best(i + 1, m1, m2 | t_mask))

        memo[key] = r
        return r

    return best(0, 0, 0)
