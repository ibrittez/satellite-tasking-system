# The allocation algorithm

How `domain/allocator.py` decides which tasks to run and on which satellite.

This document follows the git history: the implementation was committed in stages, from
the most naive correct version to the current one. Each section shows what changed and
why, so the reasoning is auditable commit by commit (or tag by tag `;)`)

| tag      | stage                                                      |
| -------- | ---------------------------------------------------------- |
| `stage1` | memoized recursion over sets                               |
| `stage2` | collapse symmetric states in the memo key                  |
| `stage3` | sets become integer bitmasks                               |
| `stage4` | return the assignment, not just the payoff                 |
| `stage5` | generalize from 2 satellites to N                          |
| `stage6` | spread the load instead of packing satellite 0             |
| `stage7` | shortcut: one satellite per task                           |
| `stage8` | shortcut: a full greedy placement as a proof of optimality |

## The problem

Every task declares a payoff and a set of exclusive resource ids. A satellite cannot hold
two tasks that share a resource id. The constraint is per satellite, so the same resource
may be used by two tasks as long as they run on different satellites.

The goal is to maximize the total payoff of the tasks that actually run. Two decisions are
coupled: which tasks to run, and where to put them. Choosing a task for one satellite
changes what the other satellites can still accept, so the decisions cannot be made
independently.

The running example, with two satellites:

| task                 | payoff | resources |
| -------------------- | ------ | --------- |
| `high_res_capture`   | 10     | {1, 5}    |
| `sensor_maintenance` | 1      | {1, 2}    |
| `comms_test`         | 5      | {5, 6}    |
| `fsck_disk_a`        | 2      | {1, 6}    |

The optimum is 16: `high_res_capture` on one satellite, `sensor_maintenance` +
`comms_test` on the other. `fsck_disk_a` is left out.

## Why not greedy

Sorting by payoff and assigning each task to the first satellite that accepts it is the
obvious approach, and it happens to find the optimum on the example above. But it is not
correct in general:

| task | payoff | resources |
| ---- | ------ | --------- |
| `a1` | 10     | {1, 2}    |
| `a2` | 10     | {1, 2}    |
| `b`  | 6      | {1}       |
| `c`  | 6      | {2}       |

Greedy places `a1` on satellite 1 and `a2` on satellite 2, which consumes resources 1 and
2 on both. `b` and `c` no longer fit anywhere: 20.

The optimum is 22: `a1` alone on satellite 1, and `b` + `c` together on satellite 2. They
share no resource with each other. Taking the second highest-payoff task was the mistake,
and greedy cannot see that because it never reconsiders.

The goal is to maximize the payoff, not to approximate it, so the allocator is
exact.

## Stage 1: memoized recursion (tag: `stage1`)

The problem is a sequence of independent decisions: for each task, either skip it, or give
it to satellite 1, or give it to satellite 2. That is a tree of `3^n` paths, which is
explored exactly by recursion.

```python
def allocate(tasks: list[Task]) -> float:
    """Return the maximum payoff achievable by allocating tasks to two groups."""
    memo: dict[tuple[int, frozenset[int], frozenset[int]], float] = {}

    def best(i: int, m1: frozenset[int], m2: frozenset[int]) -> float:
        if i == len(tasks):
            return 0.0

        key = (i, m1, m2)
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
```

`best(i, m1, m2)` answers one question: given that satellite 1 has already committed the
resources in `m1` and satellite 2 those in `m2`, what is the best payoff obtainable from
tasks `i` onward? The three branches are the three choices, and `max` keeps the best one.
`t.resources & m1` is the conflict test, a non-empty intersection means that satellite
cannot take the task.

The memo is what makes this tractable. Many different sequences of decisions lead to the
same `(i, m1, m2)`, and from that point on the answer is identical, so it is computed once
and reused. Without it the recursion is exponential in the number of tasks; with it, the
cost is bounded by the number of distinct states.

## Stage 2: collapse symmetric states (tag: `stage2`)

The satellites are interchangeable. Nothing in the problem distinguishes satellite 1 from
satellite 2, so the state "satellite 1 holds {1,5}, satellite 2 holds {2}" has exactly the
same answer as "satellite 1 holds {2}, satellite 2 holds {1,5}". The first version
computed and stored both.

```diff
-        key = (i, m1, m2)
+        m_lo, m_hi = sorted((m1, m2), key=sorted)
+        key = (i, m_lo, m_hi)
```

Sorting the two masks before building the key makes the two permutations map to the same
entry, roughly halving the number of states.

## Stage 3: bitmasks instead of sets (tag:`stage3`)

The masks are precomputed once into `resources_bitmasks`, so the conversion cost
is paid `n` times rather than once per visited state. Measured effect: execution
time dropped by almost half.

```diff
+def resources_to_bitmask(resources: frozenset[int]) -> int:
+    mask = 0
+    for r in resources:
+        mask |= 1 << r
+    return mask
```

```diff
-        m_lo, m_hi = sorted((m1, m2), key=sorted)
-        key = (i, m_lo, m_hi)
+        lo, hi = (m1, m2) if m1 <= m2 else (m2, m1)
+        key = (i, lo, hi)
```

```diff
-        if not (t.resources & m1):
-            r = max(r, t.payoff + best(i + 1, m1 | t.resources, m2))
+        t_mask = resources_bitmasks[i]
+        if not (t_mask & m1):
+            r = max(r, tasks[i].payoff + best(i + 1, m1 | t_mask, m2))
```

## Stage 4: return the assignment (tag: `stage4`)

Up to here the allocator returned only the maximum payoff. The GroundStation
needs to know which task goes to which satellite.

Since all the needed nodes are already calculated and stored in memo, we can make a second
pass reconstructiong the decision tree.

```python
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
```

The idea: at state `(i, m1, m2)` the optimal value is known (`target`). Whichever branch
reproduces `target` is a branch the optimum could have taken, so follow it and move to the
state it leads to. Every `best(...)` call here is a memo hit, because the first pass
already filled every reachable state, so the whole pass is `O(n)`.

## Stage 5: N-satellites support (tag: `stage5`)

We finally generalizes the two masks into a tuple of `sat_count` masks.

```diff
-    def best(i: int, m1: int, m2: int) -> float:
-        lo, hi = (m1, m2) if m1 <= m2 else (m2, m1)
-        key = (i, lo, hi)
+    def best(i: int, sat_res: tuple[int, ...]) -> float:
+        key = (i, *sorted(sat_res))
```

This costs roughly 1.25x to 1.5x in runtime. Passing and sorting a tuple is inherently more
expensive than two integers, and it is the price of supporting a configurable fleet size.

Thats why we modified the timeout of the benchmark test `test_allocate_finishes_within_time_budget`

## Stage 6: spread the load (tag: `stage6`)

The memo stores payoffs, not decisions, so reconstruction asks it "is this placement still
on an optimal path?". In the example above, with four satellites, several placements
answer yes. The first version took the first one it found:

```python
        for s in range(sat_count):
            if not (t_mask & sat_resources[s]):
                new = ...
                if task.payoff + best(i + 1, new) == target:
                    groups[s].append(task)
                    sat_resources = new
                    break
```

`range(sat_count)` plus `break` means the lowest index always wins, so tasks pile
onto satellite 0 while the rest of the fleet idles. Nothing was optimizing for
that; the loop simply never looked at the other satellites.

The fix is to stop early-exiting and pick among the placements that tie:

```python
chosen: int | None = None
chosen_res: tuple[int, ...] = sat_resources

for s in range(sat_count):
    if t_mask & sat_resources[s]:
        continue                  # s already holds one of these resources

    new = ...
    if task.payoff + best(i + 1, new) != target:
        continue                  # placing it here would cost payoff later

    if chosen is None or len(groups[s]) < len(groups[chosen]):
        chosen = s                # first valid one, or a less loaded one
        chosen_res = new

if chosen is not None:
    groups[chosen].append(task)
    sat_resources = chosen_res
```

To understand the algorithm we suggest you to follow the example at
`docs/allocator_load_spread_example.md`

## Stage 7: one satellite per task (tag: `stage7`)

If there are at least as many satellites as tasks, give each task its own
satellite. No group holds two tasks, so no resource conflict is possible, and
every payoff is collected:

```python
    if sat_count >= len(tasks):
        total = sum(task.payoff for task in tasks)
        assignments = [Assignment(s, (task,)) for s, task in enumerate(tasks)]
        assignments += [Assignment(s, ()) for s in range(len(tasks), sat_count)]
        return total, assignments
```

This is not a micro-optimization. A state holds one mask per satellite, so a
large fleet is the worst shape for the DP, and this is the shape whose answer
is the most obvious one to ask for: 10 tasks on 10 satellites did not finish
in 180 seconds of search; the guard answers in `O(n)`.

## Stage 8: a full placement is a proof

`Task.__post_init__` rejects a payoff of zero or less, so every task adds value
and `sum(payoffs)` is a hard upper bound: no allocation can be worth more than
running everything.

In this case we can solve following a greedy approach.

```python
def _greedy_allocation(tasks: list[Task], sat_count: int) -> list[list[Task]] | None:
    groups: list[list[Task]] = [[] for _ in range(sat_count)]
    claimed: list[int] = [0] * sat_count

    for task in sorted(tasks, key=_resource_count, reverse=True):
        t_mask = _resources_to_bitmask(task.resources)

        chosen: int | None = None
        for s in range(sat_count):
            if t_mask & claimed[s]:
                continue

            if chosen is None or len(groups[s]) < len(groups[chosen]):
                chosen = s

        if chosen is None:
            return None

        groups[chosen].append(task)
        claimed[chosen] |= t_mask

    return groups
```

Notices that, if at any moment, a given task is unable to be assigned we return `None`
discarding all the work and forcing the need of the DP approach solution.

Tasks are visited in descending resource count. A task claiming many resources fits
nowhere once the fleet is busy, so it has to claim a satellite while they are still free.

## Complexity and measured limits

Three paths reach an answer, and only the last one searches:

| path                   | cost               | when it applies             |
| ---------------------- | ------------------ | --------------------------- |
| one satellite per task | `O(n)`             | `sat_count >= len(tasks)`   |
| greedy full placement  | `O(n * sat_count)` | every task fits somewhere   |
| dynamic programming    | exponential        | some task has to be dropped |

A necessary condition for either shortcut is `sat_count >= max(tasks using one resource)`:
if 20 tasks claim resource 5, they need 20 distinct satellites and no full placement exists below that.

With `n` tasks, `R` distinct resources and `N` satellites, a DP state is a task index plus
one mask per satellite, so the state space is bounded by `n * (2^R)^N`. The algorithm is
linear in the number of tasks but exponential in resources and satellites. In practice
only reachable states are visited, which is far fewer than the bound.
