from multiprocessing import Process

from sat_task_system.config import Config, parse_config
from sat_task_system.ipc.channels import Channels, create_channels
from sat_task_system.loaders.json_task_source import JsonTaskSource
from sat_task_system.ports.reporter import Reporter
from sat_task_system.ports.task_source import TaskSource
from sat_task_system.processes.ground_station import GroundStation
from sat_task_system.processes.satellite import Satellite
from sat_task_system.reporting.console_reporter import ConsoleReporter

# =======================================
# main
# =======================================


def main() -> None:
    config: Config = parse_config()

    print(config, end="\n\n")

    channels: Channels = create_channels(config.sat_count)

    task_source: TaskSource = JsonTaskSource(config.tasks_path)
    reporter: Reporter = ConsoleReporter()

    processes: list[Process] = [
        *_satellite_processes(config, channels),
        _ground_station_process(config, channels, task_source, reporter),
    ]

    for process in processes:
        process.start()

    _shutdown(processes, config.join_timeout)

# =======================================
# helpers
# =======================================


def _satellite_processes(config: Config,
                         channels: Channels) -> list[Process]:
    """One process per satellite, each holding its own uplink, its own failure
    rate and the shared downlink."""
    # Config guarantees one rate per satellite, so enumerate covers the fleet.
    satellites = [
        Satellite(
            sat_id,
            failure_rate,
            channels.uplinks[sat_id],
            channels.downlink
        )
        for sat_id, failure_rate in enumerate(config.failure_rates)
    ]

    return [Process(target=satellite.run, name=f"satellite-{sat_id}")
            for sat_id, satellite in enumerate(satellites)]


def _ground_station_process(config: Config,
                            channels: Channels,
                            task_source: TaskSource,
                            reporter: Reporter) -> Process:
    """The station process, wired to the ports main() picked."""
    ground_station = GroundStation(
        source=task_source, reporter=reporter, channels=channels,
        sat_count=config.sat_count, collect_timeout=config.collect_timeout)

    return Process(target=ground_station.run, name="ground-station")


def _shutdown(processes: list[Process], timeout: float) -> None:
    """Wait for a clean exit, then kill whatever is still blocked on a queue."""
    for process in processes:
        process.join(timeout=timeout)

        if process.is_alive():
            process.terminate()
            process.join()


# =======================================
# __main__
# =======================================

if __name__ == "__main__":
    main()
