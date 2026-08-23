from sat_task_system.domain.models import Task


def resources_to_bitmask(resources: frozenset[int]) -> int:
    mask = 0
    for r in resources:
        mask |= 1 << r
    return mask


def allocate(tasks: list[Task], sat_count: int = 2) -> tuple[float, list[list[Task]]]:
    n = len(tasks)
    resources_bitmasks = [resources_to_bitmask(t.resources) for t in tasks]
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

    # Reconstruction pass: replay forward, reusing the memo (all O(1) lookups)
    # to figure out which branch matched the optimum at each step.
    groups: list[list[Task]] = [[] for _ in range(sat_count)]
    sat_resources: tuple[int, ...] = (0,)*sat_count
    for i, task in enumerate(tasks):
        t_mask = resources_bitmasks[i]
        target = best(i, sat_resources)

        for s in range(sat_count):
            if not (t_mask & sat_resources[s]):
                new = sat_resources[:s] + (sat_resources[s]
                                           | t_mask,) + sat_resources[s + 1:]
                if task.payoff + best(i+1, new) == target:
                    groups[s].append(task)
                    sat_resources = new
                    break
        # else: task was skipped

    return total, groups
