from multiprocessing import Process

from sat_task_system.config import MODE_WEB, Config, parse_config
from sat_task_system.ipc.channels import Channels, create_channels
from sat_task_system.loaders.json_task_source import JsonTaskSource
from sat_task_system.ports.reporter import Reporter
from sat_task_system.ports.task_source import TaskSource
from sat_task_system.processes.fleet import satellite_processes, shutdown
from sat_task_system.processes.ground_station import GroundStation
from sat_task_system.reporting.console_reporter import ConsoleReporter

WEB_MISSING = ("--web needs Flask, which is an optional dependency: "
               "pip install '.[web]'")

# =======================================
# main
# =======================================


def main() -> None:
    config: Config = parse_config()

    print(config, end="\n\n")

    if config.mode == MODE_WEB:
        _serve(config)
    else:
        _run_once(config)


# =======================================
# modes
# =======================================


def _run_once(config: Config) -> None:
    """One batch from the task file, station and satellites each in their own
    process, report on stdout."""
    # Config guarantees a path in cli mode; this is the narrowing, not a check.
    if config.tasks_path is None:
        raise ValueError("cli mode reached without a task file")

    channels: Channels = create_channels(config.sat_count)

    task_source: TaskSource = JsonTaskSource(config.tasks_path)
    reporter: Reporter = ConsoleReporter()

    processes: list[Process] = [
        *satellite_processes(config.failure_rates, channels),
        _ground_station_process(config, channels, task_source, reporter),
    ]

    for process in processes:
        process.start()

    shutdown(processes, config.join_timeout)


def _serve(config: Config) -> None:
    """Hand over to the web mode. Imported here, not at module level, so the cli
    keeps working without the optional dependency installed."""
    try:
        from sat_task_system.web.app import serve
    except ImportError as error:
        raise SystemExit(WEB_MISSING) from error

    serve(config)


# =======================================
# helpers
# =======================================


def _ground_station_process(config: Config,
                            channels: Channels,
                            task_source: TaskSource,
                            reporter: Reporter) -> Process:
    """The station process, wired to the ports main() picked."""
    ground_station = GroundStation(
        source=task_source, reporter=reporter, channels=channels,
        sat_count=config.sat_count, collect_timeout=config.collect_timeout)

    return Process(target=ground_station.run, name="ground-station")


# =======================================
# __main__
# =======================================

if __name__ == "__main__":
    main()
