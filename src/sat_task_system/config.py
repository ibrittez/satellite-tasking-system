from dataclasses import dataclass
from pathlib import Path

SAT_COUNT = 2
FAILURE_RATE = 0.10

COLLECT_TIMEOUT = 5.0
JOIN_TIMEOUT = 5.0

TASKS_FILE = Path(__file__).resolve().parents[2] / "data" / "spec_tasks.json"

@dataclass(frozen=True, slots=True)
class Config:
    tasks_path: str
    sat_count: int
    failure_rates: tuple[float, ...]   # one per satellite
    collect_timeout: float
    join_timeout: float


def parse_config() -> Config:
    return Config(str(TASKS_FILE), SAT_COUNT, (FAILURE_RATE,)*SAT_COUNT,
                  COLLECT_TIMEOUT, JOIN_TIMEOUT)
