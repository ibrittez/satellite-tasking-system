from multiprocessing import Process

from sat_task_system.config import Config, parse_config
from sat_task_system.ipc.channels import Channels, create_channels
from sat_task_system.loaders.json_task_source import JsonTaskSource
from sat_task_system.processes.ground_station import GroundStation
from sat_task_system.processes.satellite import Satellite
from sat_task_system.reporting.console_reporter import ConsoleReporter


def main() -> None:
    config: Config = parse_config()

    task_source = JsonTaskSource(config.tasks_path)
    reporter = ConsoleReporter()

    channels: Channels = create_channels(config.sat_count)

    processes: list[Process] = []
    for sat_id in range(config.sat_count):
        processes.append(Process(target=Satellite(
            sat_id, config.failure_rates[sat_id], channels.uplinks[sat_id], channels.downlink).run, name=f"satellite-{sat_id}"))

    gs: GroundStation = GroundStation(
        source=task_source, reporter=reporter, collect_timeout=config.collect_timeout, channels=channels,
        sat_count=config.sat_count)

    processes.append(Process(target=gs.run, name='ground_station'))

    for process in processes:
        process.start()

    _shutdown(processes, config.join_timeout)


def _shutdown(processes: list[Process], timeout: float) -> None:
    """Wait for a clean exit, then kill whatever is still blocked on a queue."""
    for process in processes:
        process.join(timeout=timeout)

        if process.is_alive():
            process.terminate()
            process.join()


if __name__ == "__main__":
    main()
