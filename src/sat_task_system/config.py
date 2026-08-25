import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from typing import override

# =======================================
# defaults
# =======================================

PROG = "sat-task-system"

MIN_SAT_COUNT = 2

SAT_COUNT = 2
FAILURE_RATE = 0.10

COLLECT_TIMEOUT = 5.0
JOIN_TIMEOUT = 5.0

# The two ways to drive the same fleet: a single run on the command line, or a
# server that runs one batch per submission.
MODE_CLI = "cli"
MODE_WEB = "web"
MODES = (MODE_CLI, MODE_WEB)

HOST = "127.0.0.1"
PORT = 5000

MIN_PORT = 1
MAX_PORT = 65535


# =======================================
# config
# =======================================


@dataclass(frozen=True, slots=True)
class Config:
    """Runtime configuration"""

    tasks_path: str | None
    sat_count: int
    failure_rates: tuple[float, ...]
    collect_timeout: float
    join_timeout: float
    mode: str = MODE_CLI
    host: str = HOST
    port: int = PORT

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(
                f"mode must be one of {', '.join(MODES)}, got '{self.mode}'")

        # A command line run has no other way to be told what to run. Web mode
        # takes its tasks from the request, so a path there is only a prefill.
        if self.mode == MODE_CLI and self.tasks_path is None:
            raise ValueError(f"tasks_path is required in {MODE_CLI} mode")

        if not MIN_PORT <= self.port <= MAX_PORT:
            raise ValueError(
                f"port must be in [{MIN_PORT}, {MAX_PORT}], got {self.port}")

        if self.sat_count < MIN_SAT_COUNT:
            raise ValueError(
                f"sat_count must be at least {MIN_SAT_COUNT}, got {self.sat_count}")

        # One rate per satellite, always. The broadcast form of the flag is
        # expanded before it gets here, so the rest of the code can index.
        if len(self.failure_rates) != self.sat_count:
            raise ValueError(
                f"failure_rates must hold one rate per satellite "
                f"({self.sat_count}), got {len(self.failure_rates)}")

        # Closed interval: 0.0 (never fails) and 1.0 (always fails) are what the
        # satellite tests use to pin an outcome without a seed.
        for sat_id, rate in enumerate(self.failure_rates):
            if not 0.0 <= rate <= 1.0:
                raise ValueError(
                    f"failure_rates[{sat_id}] must be in [0, 1], got {rate}")

        if self.collect_timeout <= 0.0:
            raise ValueError(
                f"collect_timeout must be positive, got {self.collect_timeout}")

        if self.join_timeout <= 0.0:
            raise ValueError(
                f"join_timeout must be positive, got {self.join_timeout}")

    @override
    def __str__(self) -> str:
        """Startup banner. Built as one string so it lands in a single write."""
        rows = [
            ("mode", self.mode),
            ("tasks", self.tasks_path or "none"),
            ("satellites", str(self.sat_count)),
            ("failure rates", ", ".join(
                f"{rate:.2f}" for rate in self.failure_rates)),
            ("collect timeout", f"{self.collect_timeout}s"),
            ("join timeout", f"{self.join_timeout}s"),
        ]

        if self.mode == MODE_WEB:
            rows.insert(1, ("listening on", f"http://{self.host}:{self.port}"))

        return "\n".join(
            [PROG, *(f"  {label:<18}{value}" for label, value in rows)])


# =======================================
# parsing
# =======================================


def parse_config(argv: Sequence[str] | None = None) -> Config:
    """Read the command line into a Config. A rejected value comes back as a
    usage error, not as a traceback -- Config owns the rules, the parser owns
    the reporting."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Annotated locals on purpose: Namespace attributes are Any, and pinning
    # them here is what keeps the type checker honest at the boundary.
    tasks_path: str | None = args.tasks
    sat_count: int = args.sat_count
    failure_rates: Sequence[float] = args.failure_rate
    collect_timeout: float = args.collect_timeout
    join_timeout: float = args.join_timeout
    mode: str = args.mode
    host: str = args.host
    port: int = args.port

    try:
        return Config(tasks_path, sat_count,
                      _expand_rates(failure_rates, sat_count),
                      collect_timeout, join_timeout, mode, host, port)
    except ValueError as error:
        parser.error(str(error))


def _expand_rates(rates: Sequence[float], sat_count: int) -> tuple[float, ...]:
    """A single rate covers the whole fleet. Any other count is passed through
    untouched, so a wrong one is rejected by Config instead of here."""
    return tuple(rates) * sat_count if len(rates) == 1 else tuple(rates)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Run a satellite fleet against a constrained task list maximizing payoff.",
        epilog=f"examples:\n"
               f"  {PROG} --tasks data/spec_tasks.json --sat-count 3 "
               f"--failure-rate 0.1 0.2 0.0\n"
               f"  {PROG} --web --tasks data/spec_tasks.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Not `required`, because web mode does not need it: Config is what rejects
    # a cli run without a path, so the rule lives with the other rules.
    _ = parser.add_argument(
        "--tasks",
        default=None,
        metavar="PATH",
        help=f"JSON file holding the task list; required in {MODE_CLI} mode, "
             f"and the box prefill in {MODE_WEB} mode",
    )

    mode = parser.add_mutually_exclusive_group()

    _ = mode.add_argument(
        "--cli",
        dest="mode",
        action="store_const",
        const=MODE_CLI,
        help="run one batch and print the report (default)",
    )

    _ = mode.add_argument(
        "--web",
        dest="mode",
        action="store_const",
        const=MODE_WEB,
        help="serve a page that runs one batch per submission",
    )

    parser.set_defaults(mode=MODE_CLI)

    _ = parser.add_argument(
        "--host",
        default=HOST,
        metavar="ADDRESS",
        help=f"address the {MODE_WEB} mode binds to (default: {HOST})",
    )

    _ = parser.add_argument(
        "--port",
        type=int,
        default=PORT,
        metavar="PORT",
        help=f"port the {MODE_WEB} mode listens on (default: {PORT})",
    )

    _ = parser.add_argument(
        "--sat-count",
        type=int,
        default=SAT_COUNT,
        metavar="N",
        help=f"satellites in the fleet, at least {MIN_SAT_COUNT} "
             f"(default: {SAT_COUNT})",
    )

    _ = parser.add_argument(
        "--failure-rate",
        nargs="+",
        type=float,
        default=(FAILURE_RATE,),
        metavar="RATE",
        help=f"probability in [0, 1] that any single task fails; one value "
             f"covers the whole fleet, or pass one per satellite "
             f"(default: {FAILURE_RATE})",
    )

    _ = parser.add_argument(
        "--collect-timeout",
        type=float,
        default=COLLECT_TIMEOUT,
        metavar="SECONDS",
        help="fleet silence tolerated before a pending result is recorded as "
             f"failed (default: {COLLECT_TIMEOUT})",
    )

    _ = parser.add_argument(
        "--join-timeout",
        type=float,
        default=JOIN_TIMEOUT,
        metavar="SECONDS",
        help="wait for a process to exit before terminating it "
             f"(default: {JOIN_TIMEOUT})",
    )

    return parser
