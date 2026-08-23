from sat_task_system.domain.models import Task


def resources_to_bitmask(resources: frozenset[int]) -> int:
    mask = 0
    for r in resources:
        mask |= 1 << r
    return mask


def allocate(tasks: list[Task]) -> tuple[float, list[list[Task]]]:
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

    total = best(0, 0, 0)

    # Reconstruction pass: replay forward, reusing the memo (all O(1) lookups)
    # to figure out which branch matched the optimum at each step.
    groups: list[list[Task]] = [[], []]
    m1 = m2 = 0
    for i, task in enumerate(tasks):
        t_mask = resources_bitmasks[i]
        target = best(i, m1, m2)

        if not (t_mask & m1) and task.payoff + best(i + 1, m1 | t_mask, m2) == target:
            groups[0].append(task)
            m1 |= t_mask
        elif not (t_mask & m2) and task.payoff + best(i + 1, m1, m2 | t_mask) == target:
            groups[1].append(task)
            m2 |= t_mask
        # else: task was skipped

    return total, groups
