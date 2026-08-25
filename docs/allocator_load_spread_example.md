# Allocator load spread example

Worked example of the load-spreader section of the allocator group assigner.

Given the following tasks:

| task                 | payoff | resources |
| -------------------- | ------ | --------- |
| `high_res_capture`   | 10     | {1, 5}    |
| `sensor_maintenance` | 1      | {1, 2}    |
| `comms_test`         | 5      | {5, 6}    |
| `fsck_disk_a`        | 2      | {1, 6}    |

After calculating the optimum payoff, `best()` (see `docs/allocator.md`) already contains
all the needed values via memoization. We can re-construct the optimum path spreeding the
load across all the posible satellites with the following code:

```python
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
```

## First example: 3 satellites

### iter 0

`i=0 — high_res_capture, payoff 10, recursos {1,5} · target = 18.0`

| s   | #tareas[s] | res[s] | conflicto | payoff + best(i+1) | == target | chosen                   |
| --- | ---------- | ------ | --------- | ------------------ | --------- | ------------------------ |
| 0   | 0          | {}     | False     | 10 + 8             | True      | None -> 0                |
| 1   | 0          | {}     | False     | 10 + 8             | True      | 0<0 = False -> sigo en 0 |
| 2   | 0          | {}     | False     | 10 + 8             | True      | 0<0 = False -> sigo en 0 |

`groups = [[high_res], [], [], []], sat_resources = ({1,5}, {}, {}, {})`

### iter 1

`i=1 — sensor_maintenance, payoff 1, {1,2} · target = 8.0`

| s   | #tareas[s] | res[s] | conflicto | payoff + best(i+1) | == target | chosen                   |
| --- | ---------- | ------ | --------- | ------------------ | --------- | ------------------------ |
| 0   | 1          | {1,5}  | True      | -                  | -         | -                        |
| 1   | 0          | {}     | False     | 1 + 7              | True      | None -> s = 1            |
| 2   | 0          | {}     | False     | 1 + 7              | True      | 0<0 = False -> sigo en 0 |

`groups = [[high_res], [maintenance], [], []], sat_resources = ({1,5}, {1,2}, {}, {})`

### iter 2

`i=2 — comms_test, payoff 5, {5,6} · target = 7.0`

| s   | #tareas[s] | res[s] | conflicto | payoff + best(i+1) | == target | chosen                   |
| --- | ---------- | ------ | --------- | ------------------ | --------- | ------------------------ |
| 0   | 1          | {1,5}  | True      | -                  | -         | -                        |
| 1   | 1          | {1,2}  | False     | 5 + 2              | True      | None -> s = 1            |
| 2   | 0          | {}     | False     | 5 + 2              | True      | 0<1 = True -> chosen = 2 |

`groups = [[high_res], [maintenance], [comms], []], sat_resources = ({1,5}, {1,2}, {5,6}, {})`

### iter 3

`i=3 — fsck_disk_a, payoff 2, {1,6} · target = 2.0`

| s   | #tareas[s] | res[s] | conflicto | payoff + best(i+1) | == target | chosen |
| --- | ---------- | ------ | --------- | ------------------ | --------- | ------ |
| 0   | 1          | {1,5}  | True      | -                  | -         | -      |
| 1   | 1          | {1,2}  | True      | -                  | -         | -      |
| 2   | 1          | {5,6}  | True      | -                  | -         | -      |

## con 4 sats

- llego igual hasta iter 2

`i=2 — comms_test, payoff 5, {5,6} · target = 7.0`

| s   | #tareas[s] | res[s] | conflicto | payoff + best(i+1) | == target | chosen                   |
| --- | ---------- | ------ | --------- | ------------------ | --------- | ------------------------ |
| 0   | 1          | {1,5}  | True      | -                  | -         | -                        |
| 1   | 1          | {1,2}  | False     | 5 + 2              | True      | None -> s = 1            |
| 2   | 0          | {}     | False     | 5 + 2              | True      | 0<1 = True -> chosen = 2 |
| 3   | 0          | {}     | False     | 5 + 2              | True      | 0<1 = True -> chosen = 2 |

`groups = [[high_res], [maintenance], [comms], []], sat_resources = ({1,5}, {1,2}, {5,6}, {})`

### iter 3

`i=3 — fsck_disk_a, payoff 2, {1,6} · target = 2.0`

| s   | #tareas[s] | res[s] | conflicto | payoff + best(i+1) | == target | chosen                 |
| --- | ---------- | ------ | --------- | ------------------ | --------- | ---------------------- |
| 0   | 1          | {1,5}  | True      | -                  | -         | -                      |
| 1   | 1          | {1,2}  | True      | -                  | -         | -                      |
| 2   | 0          | {5,6}  | False     | -                  | -         | -                      |
| 3   | 0          | {}     | False     | 2 + 0              | True      | None -> chosen = s = 3 |

`groups = [[high_res], [maintenance], [comms], [fsck_disk_a]], sat_resources = ({1,5}, {1,2}, {5,6}, {1,6})`
