# Persistence

Scope: how a finished run is recorded and read back. The front end that exposes it is
covered in `docs/web.md`, the layering in `docs/architecture.md`.

## Where it attaches

Recording a run is what `Reporter` already describes: publish is terminal, called once, and
receives the whole `Summary`. So persistence is an implementation of that port, not a new
concern for the station to know about:

```python
class SqliteReporter(Reporter):
    def __init__(self, db_path: str) -> None:
        self._store = SqliteStore(db_path)

    @override
    def publish(self, summary: Summary) -> None:
        _ = self._store.save(summary)
```

Two destinations are needed at once, since the web mode also has to read the summary back
into the response. `MultiReporter` is what composes them:

```python
station = GroundStation(reporter=MultiReporter((capture, recorder)), ...)
```

A `Reporter` holding `Reporter`s satisfies the same contract, so the station still publishes
once and remains unaware of how many destinations exist. `MultiReporter` does not extend the
single-write promise across its members: each one keeps its own, and a member that raises
stops the ones behind it.

The reporter is thin on purpose. `SqliteStore` owns the schema and the SQL, and is usable
without the port, which is what lets the history page query it directly instead of going
through an interface built for writing.

## Schema

```sql
CREATE TABLE runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT    NOT NULL,
    sat_count       INTEGER NOT NULL,
    planned_payoff  REAL    NOT NULL,
    achieved_payoff REAL    NOT NULL
);

CREATE TABLE task_results (
    run_id       INTEGER NOT NULL REFERENCES runs(id),
    satellite_id INTEGER,
    task_name    TEXT    NOT NULL,
    payoff       REAL    NOT NULL,
    resources    TEXT    NOT NULL,
    outcome      TEXT    NOT NULL CHECK (outcome IN ('ok', 'failed', 'skipped'))
);
```

Two tables, not one. A run has a header and a variable number of task rows, so flattening it
into a single row would mean storing the task list as text: the database would then hold a
rendered report rather than data, and nothing could be counted or filtered.

| column                     | why it looks like that                                                                                                          |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `runs.created_at`          | ISO 8601 UTC, stamped by the store. A `Summary` has no notion of time, so what is recorded is when the run was stored.           |
| `runs.planned_payoff`      | Both totals are properties on `Summary`, so the header row is a direct read.                                                     |
| `task_results.satellite_id` | Nullable, and null means skipped. A task no satellite could take has no satellite id, and inventing one would corrupt the query. |
| `task_results.outcome`     | One column with a `CHECK` instead of two booleans: the three states are mutually exclusive, and an invalid row cannot be written. |
| `task_results.resources`   | The sorted ids, comma separated. Denormalized on purpose: the history page displays them and nothing joins on them.              |

Every task the run accounted for gets a row, dispatched or skipped, so the number of rows
per run is the size of the submitted list.

The schema is created with `IF NOT EXISTS` on every connection, which makes it idempotent
and removes the separate migration step there would otherwise be to forget.

## The store holds a path

`SqliteStore` keeps the file path and opens a connection per call. Two reasons, both
concrete:

1. A `sqlite3.Connection` belongs to the thread that created it, and the server answers
   requests from a thread pool.
2. A connection does not pickle. `JsonTaskSource` holds a path for the same reason: an
   adapter injected into the station may be pickled into a child process.

Writing is one transaction, which is what `publish()` being called once maps onto:

```python
with closing(self._connect()) as connection, connection:
    cursor = connection.execute(INSERT_RUN, ...)
    run_id = cursor.lastrowid
    connection.executemany(INSERT_TASK, self._task_rows(run_id, summary))
```

The two context managers do different jobs, and both are needed: `closing()` closes the
connection, while the connection itself commits on a clean exit and rolls back on an
exception. A crash mid write leaves no half recorded run.

## Reading it back

```python
def recent_runs(self, limit: int = HISTORY_LIMIT) -> list[StoredRun]
```

The newest runs first, each carrying its own task rows, as two queries and a grouping pass
in Python. One query per run would be a query per row of the page; a single join would
return the header columns repeated once per task and need the same grouping anyway.

The task query builds its `IN` list from a placeholder count, never from values:

```python
query = SELECT_TASKS.format(placeholders=", ".join("?" * len(run_ids)))
task_rows = connection.execute(query, run_ids).fetchall()
```

The ids are still bound parameters. String formatting only decides how many `?` there are,
which is the part SQLite cannot parameterize.

Rows come back as `StoredRun` and `StoredTask`, frozen dataclasses declared next to the
queries. They are read models, not domain types: the domain has `Task` and `TaskResult` for
a run that is happening, and these describe a run that already happened, including the
`outcome` state that only exists once it is over.

## Opt in

Recording is off unless a path is given:

```bash
sat-task-system --web --db runs.db
```

`--db` applies to the web mode, which is the mode that can read the history back, and
`Config` rejects it elsewhere rather than accepting a flag that would do nothing. With no
path, the history link is absent from the page and `/history` answers that nothing is being
recorded.

## Limits

- A failing write fails the request. The run happened, the summary was captured, and then
  `MultiReporter` reached a member that raised, so the response is a server error rather
  than a report with a warning. Deciding otherwise means deciding whether an unrecorded run
  counts as successful, which is a policy question and not a code one.
- No pruning and no pagination. The history page reads the most recent runs, and the file
  grows for as long as runs are submitted.
- One writer. The one-run-at-a-time rule of the web mode is what keeps that true; a second
  process pointed at the same file would meet SQLite's own locking, not this design's.
