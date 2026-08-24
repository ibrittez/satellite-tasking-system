import pytest

from sat_task_system.config import (COLLECT_TIMEOUT, FAILURE_RATE,
                                    JOIN_TIMEOUT, MIN_SAT_COUNT, SAT_COUNT,
                                    Config, parse_config)

TASKS = "data/spec_tasks.json"
BASE_ARGV = ["--tasks", TASKS]

USAGE_ERROR = 2


# =======================================
# helpers
# =======================================


def make_config(tasks_path: str = TASKS,
                sat_count: int = 2,
                failure_rates: tuple[float, ...] = (0.1, 0.1),
                collect_timeout: float = 5.0,
                join_timeout: float = 5.0) -> Config:
    """A valid Config, so each test only spells out the field it is probing."""
    return Config(tasks_path, sat_count, failure_rates,
                  collect_timeout, join_timeout)


def value_for(banner: str, label: str) -> str:
    """The value printed next to `label`, so assertions ignore alignment."""
    matches = [line.strip().removeprefix(label).strip()
               for line in banner.splitlines()
               if line.strip().startswith(label)]
    assert len(
        matches) == 1, f"expected one row for {label!r}, got {matches}"
    return matches[0]


# =======================================
# __post_init__
# =======================================


def test_a_fleet_below_the_minimum_is_rejected():
    """The spec needs at least two satellites, so a smaller fleet cannot exist."""
    with pytest.raises(ValueError, match="sat_count"):
        _ = make_config(sat_count=MIN_SAT_COUNT - 1)


def test_a_failure_rate_outside_the_unit_interval_is_rejected():
    """A probability above 1 or below 0 is not a probability, and the offending
    satellite is named."""
    with pytest.raises(ValueError, match=r"failure_rates\[1\]"):
        _ = make_config(failure_rates=(0.1, 1.5))

    with pytest.raises(ValueError, match=r"failure_rates\[0\]"):
        _ = make_config(failure_rates=(-0.1, 0.1))


def test_both_ends_of_the_unit_interval_are_accepted():
    """0.0 (never fails) and 1.0 (always fails) are the values the satellite
    tests use to pin an outcome without a seed -- the interval stays closed."""
    assert make_config(failure_rates=(0.0, 1.0)).failure_rates == (0.0, 1.0)


def test_a_rate_count_other_than_one_per_satellite_is_rejected():
    """Downstream code indexes the rates by satellite id, so the fleet and the
    tuple must have the same size."""
    with pytest.raises(ValueError, match="failure_rates"):
        _ = make_config(sat_count=3, failure_rates=(0.1, 0.2))


def test_a_non_positive_timeout_is_rejected():
    """A zero or negative wait would turn both timeouts into instant giving up."""
    with pytest.raises(ValueError, match="collect_timeout"):
        _ = make_config(collect_timeout=0.0)

    with pytest.raises(ValueError, match="join_timeout"):
        _ = make_config(join_timeout=-1.0)

# =======================================
# parse_config
# =======================================


def test_only_the_task_file_is_required():
    """Everything else falls back to its default."""
    config = parse_config(BASE_ARGV)

    assert config == Config(TASKS, SAT_COUNT, (FAILURE_RATE,) * SAT_COUNT,
                            COLLECT_TIMEOUT, JOIN_TIMEOUT)


def test_every_setting_can_be_overridden():
    """Each flag reaches its field."""
    config = parse_config([*BASE_ARGV,
                           "--sat-count", "3",
                           "--failure-rate", "0.3", "0.0", "1.0",
                           "--collect-timeout", "2.5",
                           "--join-timeout", "1.5"])

    assert config == Config(TASKS, 3, (0.3, 0.0, 1.0), 2.5, 1.5)


def test_a_rejected_value_exits_as_a_usage_error(capsys: pytest.CaptureFixture[str]):
    """A broken rule reaches the user as usage text, not as a traceback."""
    with pytest.raises(SystemExit) as exit_info:
        _ = parse_config([*BASE_ARGV, "--sat-count", str(MIN_SAT_COUNT - 1)])

    assert exit_info.value.code == USAGE_ERROR
    assert "sat_count" in capsys.readouterr().err


def test_a_missing_task_file_is_a_usage_error():
    """There is no default path to fall back to, so --tasks cannot be omitted."""
    with pytest.raises(SystemExit) as exit_info:
        _ = parse_config([])

    assert exit_info.value.code == USAGE_ERROR


def test_a_non_numeric_value_is_a_usage_error():
    """Type conversion fails before any rule is checked."""
    with pytest.raises(SystemExit) as exit_info:
        _ = parse_config([*BASE_ARGV, "--sat-count", "many"])

    assert exit_info.value.code == USAGE_ERROR
