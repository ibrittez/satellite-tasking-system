"""The web mode: paste a task list, run the fleet, read the report.

One page and one form, plus a few lines of script that clear the previous report
on submit. A submission is one batch: the tasks are validated here, before any
process is started, so a malformed list comes back as a message instead of as a
half-run fleet.
"""

import json
import threading

from flask import Flask, render_template, request

from sat_task_system.config import Config
from sat_task_system.loaders.json_task_loader import parse_tasks
from sat_task_system.processes.fleet import run_batch
from sat_task_system.reporting.text_report import render_summary

PAGE = "index.html"

BAD_REQUEST = 400
CONFLICT = 409

BUSY = "A run is already in flight. Wait for it to finish and submit again."

# =======================================
# app
# =======================================


def create_app(config: Config) -> Flask:
    """The application, wired to one fleet configuration. Takes a Config instead
    of reading one, so a test can drive it without a command line."""
    app = Flask(__name__)

    # One fleet at a time: two concurrent runs would compete for the machine and
    # report over each other. The honest small answer, a job queue is the real one.
    running = threading.Lock()

    @app.get("/")
    def index() -> str:
        return _page(config, _prefill(config))

    @app.post("/")
    def submit() -> str | tuple[str, int]:
        submitted: str = request.form.get("tasks", "")

        try:
            # JSONDecodeError is a ValueError, and so is every parse_tasks
            # rejection, so both arrive here as a message worth showing.
            tasks = parse_tasks(json.loads(submitted))
        except ValueError as error:
            return _page(config, submitted, error=str(error)), BAD_REQUEST

        if not running.acquire(blocking=False):
            return _page(config, submitted, error=BUSY), CONFLICT

        try:
            summary = run_batch(tasks, config)
        finally:
            running.release()

        return _page(config, submitted, report=render_summary(summary))

    return app


def serve(config: Config) -> None:
    """Run the server. Debug stays off: the reloader re-executes the module, and
    this one spawns processes."""
    create_app(config).run(host=config.host, port=config.port)


# =======================================
# helpers
# =======================================


def _page(config: Config,
          submitted: str,
          report: str | None = None,
          error: str | None = None) -> str:
    """The single template, rendered with whatever this request produced."""
    return render_template(PAGE,
                           tasks=submitted,
                           report=report,
                           error=error,
                           sat_count=config.sat_count,
                           failure_rates=", ".join(
                               f"{rate:.2f}" for rate in config.failure_rates))


def _prefill(config: Config) -> str:
    """The --tasks file, so the box opens with something runnable. Optional in
    this mode, and unreadable is the same as absent: the box just starts empty."""
    if config.tasks_path is None:
        return ""

    try:
        with open(config.tasks_path, "r") as file:
            return file.read()
    except OSError:
        return ""
