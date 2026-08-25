from sat_task_system.domain.models import Assignment, Task


# =======================================
# helpers
# =======================================

def _resources_to_bitmask(resources: frozenset[int]) -> int:
    mask = 0
    for r in resources:
        mask |= 1 << r
    return mask


def _resource_count(task: Task) -> int:
    return len(task.resources)


# =======================================
# greedy
# =======================================

def _greedy_allocation(tasks: list[Task], sat_count: int) -> list[list[Task]] | None:
    """Try to place every task, hardest first, on the least loaded satellite that holds
    none of its resources. Returns None as soon as one task fits nowhere."""
    groups: list[list[Task]] = [[] for _ in range(sat_count)]
    claimed: list[int] = [0] * sat_count

    # Hardest first: a task claiming many resources fits nowhere once the fleet is busy.
    for task in sorted(tasks, key=_resource_count, reverse=True):
        t_mask = _resources_to_bitmask(task.resources)

        chosen: int | None = None
        for s in range(sat_count):
            if t_mask & claimed[s]:
                continue

            # load distribution
            if chosen is None or len(groups[s]) < len(groups[chosen]):
                chosen = s

        # no satellite can take this task
        if chosen is None:
            return None

        groups[chosen].append(task)
        claimed[chosen] |= t_mask

    return groups


# =======================================
# allocation
# =======================================

def allocate(tasks: list[Task], sat_count: int = 2) -> tuple[float, list[Assignment]]:
    n = len(tasks)

    # One task per satellite: no group holds two tasks, so no resource conflict
    if sat_count >= n:
        total = sum(task.payoff for task in tasks)
        a = [Assignment(s, (task,)) for s, task in enumerate(tasks)]
        a += [Assignment(s, ()) for s in range(len(tasks), sat_count)]
        return total, a

    # If there is a combination where no resources conflict, we can assign all
    # tasks and obtain the optimum without solving by DP.
    greedy_groups = _greedy_allocation(tasks, sat_count)
    if greedy_groups is not None:
        total = sum(task.payoff for task in tasks)
        return total, [Assignment(s, tuple(group))
                       for s, group in enumerate(greedy_groups)]

    # DP approach
    resources_bitmasks = [_resources_to_bitmask(t.resources) for t in tasks]
    payoffs = [t.payoff for t in tasks]

    # memoization storage. ([int, ...]: task index, then one mask per satellite).
    memo: dict[tuple[int, ...], float] = {}

    def best(i: int, sat_res: tuple[int, ...]) -> float:
        if i == n:
            return 0.0

        key = (i, *sorted(sat_res))
        cached = memo.get(key)
        if cached is not None:
            return cached

        t_mask = resources_bitmasks[i]
        payoff = payoffs[i]

        r = best(i + 1, sat_res)

        for idx, res in enumerate(sat_res):
            if not (t_mask & res):
                new_res = sat_res[:idx] + (res | t_mask,) + sat_res[idx + 1:]
                candidate = payoff + best(i+1, new_res)
                if candidate > r:
                    r = candidate

        memo[key] = r
        return r

    total = best(0, (0,) * sat_count)

    # Reconstruction pass: replay forward, reusing the memo (all O(1) lookups) to
    # figure out which branch matched the optimum at each step. Among the placements
    # that tie on payoff, the least loaded satellite wins.
    groups: list[list[Task]] = [[] for _ in range(sat_count)]
    sat_resources: tuple[int, ...] = (0,)*sat_count

    for i, task in enumerate(tasks):
        t_mask = resources_bitmasks[i]
        target = best(i, sat_resources)

        chosen: int | None = None
        chosen_res: tuple[int, ...] = sat_resources

        for s in range(sat_count):
            if t_mask & sat_resources[s]:
                continue

            new = (sat_resources[:s] + (sat_resources[s]
                   | t_mask,) + sat_resources[s + 1:])

            if task.payoff + best(i+1, new) != target:
                continue

            if chosen is None or len(groups[s]) < len(groups[chosen]):
                chosen = s
                chosen_res = new

        if chosen is not None:
            groups[chosen].append(task)
            sat_resources = chosen_res

    return total, [Assignment(s, tuple(group)) for s, group in enumerate(groups)]
