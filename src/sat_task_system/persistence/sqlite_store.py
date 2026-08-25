"""Run history on SQLite: the write side and the queries the history page needs.

Holds a path, never an open connection. A connection is per call, which is what
makes the store usable from a server thread pool: a sqlite3 connection belongs
to the thread that created it.
"""

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime

from sat_task_system.domain.models import Summary

HISTORY_LIMIT = 20

OK = "ok"
FAILED = "failed"
SKIPPED = "skipped"

# =======================================
# schema
# =======================================

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at      TEXT    NOT NULL,
    sat_count       INTEGER NOT NULL,
    planned_payoff  REAL    NOT NULL,
    achieved_payoff REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS task_results (
    run_id       INTEGER NOT NULL REFERENCES runs(id),
    satellite_id INTEGER,
    task_name    TEXT    NOT NULL,
    payoff       REAL    NOT NULL,
    resources    TEXT    NOT NULL,
    outcome      TEXT    NOT NULL CHECK (outcome IN ('ok', 'failed', 'skipped'))
);

CREATE INDEX IF NOT EXISTS task_results_by_run ON task_results(run_id);
"""

INSERT_RUN = """
INSERT INTO runs (created_at, sat_count, planned_payoff, achieved_payoff)
VALUES (?, ?, ?, ?)
"""

INSERT_TASK = """
INSERT INTO task_results
    (run_id, satellite_id, task_name, payoff, resources, outcome)
VALUES (?, ?, ?, ?, ?, ?)
"""

SELECT_RUNS = """
SELECT id, created_at, sat_count, planned_payoff, achieved_payoff
FROM runs
ORDER BY id DESC
LIMIT ?
"""

# The IN list is built from a placeholder count, never from values.
SELECT_TASKS = """
SELECT run_id, satellite_id, task_name, payoff, resources, outcome
FROM task_results
WHERE run_id IN ({placeholders})
ORDER BY rowid
"""


# =======================================
# read models
# =======================================


@dataclass(frozen=True, slots=True)
class StoredTask:
    """One task row as stored. `satellite_id` is None for a skipped task."""

    satellite_id: int | None
    task_name: str
    payoff: float
    resources: str
    outcome: str


@dataclass(frozen=True, slots=True)
class StoredRun:
    """One finished run, with the tasks it accounted for."""

    run_id: int
    created_at: str
    sat_count: int
    planned_payoff: float
    achieved_payoff: float
    tasks: tuple[StoredTask, ...]

    @property
    def skipped_count(self) -> int:
        return sum(1 for task in self.tasks if task.outcome == SKIPPED)

    @property
    def failed_count(self) -> int:
        return sum(1 for task in self.tasks if task.outcome == FAILED)


# =======================================
# store
# =======================================


class SqliteStore:
    def __init__(self, db_path: str) -> None:
        self._path: str = db_path

    def save(self, summary: Summary) -> int:
        """Insert one run and its task rows in a single transaction, and return
        the id it was given."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                INSERT_RUN,
                (self._now(), len(summary.assignments),
                 summary.planned_payoff, summary.achieved_payoff))

            run_id = cursor.lastrowid
            if run_id is None:
                raise RuntimeError("sqlite did not report an id for the run")

            _ = connection.executemany(INSERT_TASK, self._task_rows(run_id, summary))

        return run_id

    def recent_runs(self, limit: int = HISTORY_LIMIT) -> list[StoredRun]:
        """The newest runs first, each carrying its own task rows."""
        with closing(self._connect()) as connection:
            runs = connection.execute(SELECT_RUNS, (limit,)).fetchall()

            if not runs:
                return []

            run_ids = [int(row["id"]) for row in runs]
            query = SELECT_TASKS.format(
                placeholders=", ".join("?" * len(run_ids)))
            task_rows = connection.execute(query, run_ids).fetchall()

        by_run: dict[int, list[StoredTask]] = {run_id: [] for run_id in run_ids}
        for row in task_rows:
            by_run[int(row["run_id"])].append(StoredTask(
                satellite_id=row["satellite_id"],
                task_name=row["task_name"],
                payoff=row["payoff"],
                resources=row["resources"],
                outcome=row["outcome"],
            ))

        return [
            StoredRun(
                run_id=int(row["id"]),
                created_at=row["created_at"],
                sat_count=row["sat_count"],
                planned_payoff=row["planned_payoff"],
                achieved_payoff=row["achieved_payoff"],
                tasks=tuple(by_run[int(row["id"])]),
            )
            for row in runs
        ]

    # =======================================
    # helpers
    # =======================================

    def _connect(self) -> sqlite3.Connection:
        """A connection with the schema in place. `IF NOT EXISTS` makes this
        idempotent, so there is no separate migration step to forget."""
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        _ = connection.executescript(SCHEMA)

        return connection

    @staticmethod
    def _now() -> str:
        """The write time. A Summary carries no timestamp, so the store stamps
        it: what is being recorded is when the run was stored."""
        return datetime.now(UTC).isoformat(timespec="seconds")

    @staticmethod
    def _task_rows(run_id: int,
                   summary: Summary) -> list[tuple[object, ...]]:
        """Every task the run accounted for: the dispatched ones with their
        outcome, then the ones no satellite could take."""
        outcomes = {result.task_name: result.success
                    for result in summary.results}

        rows: list[tuple[object, ...]] = [
            (run_id, assignment.satellite_id, task.name, task.payoff,
             _resources(task.resources), OK if outcomes[task.name] else FAILED)
            for assignment in summary.assignments
            for task in assignment.tasks
        ]

        rows.extend(
            (run_id, None, task.name, task.payoff,
             _resources(task.resources), SKIPPED)
            for task in summary.skipped
        )

        return rows


def _resources(resources: frozenset[int]) -> str:
    """Sorted, because frozenset iteration order is not guaranteed."""
    return ", ".join(str(resource) for resource in sorted(resources))
