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


# =======================================
# config
# =======================================


@dataclass(frozen=True, slots=True)
class Config:
    """Runtime configuration"""

    tasks_path: str
    sat_count: int
    failure_rate: float
    collect_timeout: float
    join_timeout: float

    def __post_init__(self) -> None:
        if self.sat_count < MIN_SAT_COUNT:
            raise ValueError(
                f"sat_count must be at least {MIN_SAT_COUNT}, got {self.sat_count}")

        # Closed interval: 0.0 (never fails) and 1.0 (always fails) are what the
        # satellite tests use to pin an outcome without a seed.
        if not 0.0 <= self.failure_rate <= 1.0:
            raise ValueError(
                f"failure_rate must be in [0, 1], got {self.failure_rate}")

        if self.collect_timeout <= 0.0:
            raise ValueError(
                f"collect_timeout must be positive, got {self.collect_timeout}")

        if self.join_timeout <= 0.0:
            raise ValueError(
                f"join_timeout must be positive, got {self.join_timeout}")

    @override
    def __str__(self) -> str:
        """Startup banner. Built as one string so it lands in a single write."""
        rows = (
            ("tasks", self.tasks_path),
            ("satellites", str(self.sat_count)),
            ("failure rate", f"{self.failure_rate:.2f}"),
            ("collect timeout", f"{self.collect_timeout}s"),
            ("join timeout", f"{self.join_timeout}s"),
        )

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
    tasks_path: str = args.tasks
    sat_count: int = args.sat_count
    failure_rate: float = args.failure_rate
    collect_timeout: float = args.collect_timeout
    join_timeout: float = args.join_timeout

    try:
        return Config(tasks_path, sat_count, failure_rate,
                      collect_timeout, join_timeout)
    except ValueError as error:
        parser.error(str(error))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Run a satellite fleet against a constrained task list maximizing payoff.",
        epilog=f"example: {PROG} --tasks data/spec_tasks.json --sat-count 3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required on purpose: an installed package has no repo tree to default to,
    # so each context (Makefile, Dockerfile) declares its own path.
    _ = parser.add_argument(
        "--tasks",
        required=True,
        metavar="PATH",
        help="JSON file holding the task list",
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
        type=float,
        default=FAILURE_RATE,
        metavar="RATE",
        help=f"probability in [0, 1] that any single task fails "
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
