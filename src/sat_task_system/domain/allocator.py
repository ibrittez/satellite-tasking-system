from sat_task_system.domain.models import Assignment, Task


def resources_to_bitmask(resources: frozenset[int]) -> int:
    mask = 0
    for r in resources:
        mask |= 1 << r
    return mask


def allocate(tasks: list[Task], sat_count: int = 2) -> tuple[float, list[Assignment]]:
    n = len(tasks)
    resources_bitmasks = [resources_to_bitmask(t.resources) for t in tasks]
    payoffs = [t.payoff for t in tasks]

    # memoization storage. ([int, ...]: task index, then one mask per satellite).
    memo: dict[tuple[int, ...], float] = {}

    # One task per satellite: no group holds two tasks, so no resource conflict
    if sat_count >= len(tasks):
        total = sum(task.payoff for task in tasks)
        a = [Assignment(s, (task,)) for s, task in enumerate(tasks)]
        a += [Assignment(s, ()) for s in range(len(tasks), sat_count)]
        return total, a

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
