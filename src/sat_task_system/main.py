from multiprocessing import Process
from pathlib import Path

from sat_task_system.ipc.channels import Channels, create_channels
from sat_task_system.loaders.json_task_source import JsonTaskSource
from sat_task_system.processes.ground_station import GroundStation
from sat_task_system.processes.satellite import Satellite
from sat_task_system.reporting.console_reporter import ConsoleReporter

SAT_COUNT = 2
FAILURE_RATE = 0.10

COLLECT_TIMEOUT = 5.0
JOIN_TIMEOUT = 5.0

TASKS_FILE = Path(__file__).resolve().parents[2] / "data" / "spec_tasks.json"

def main() -> None:
    task_source = JsonTaskSource(str(TASKS_FILE))
    reporter = ConsoleReporter()

    channels: Channels = create_channels(SAT_COUNT)

    processes: list[Process] = []
    for sat_id in range(SAT_COUNT):
        processes.append(Process(target=Satellite(
            sat_id, FAILURE_RATE, channels.uplinks[sat_id], channels.downlink).run, name=f"satellite-{sat_id}"))

    gs: GroundStation = GroundStation(
        source=task_source, reporter=reporter, collect_timeout=COLLECT_TIMEOUT, channels=channels,
        sat_count=SAT_COUNT)

    processes.append(Process(target=gs.run, name='ground_station'))

    for process in processes:
        process.start()

    _shutdown(processes)


def _shutdown(processes: list[Process]) -> None:
    """Wait for a clean exit, then kill whatever is still blocked on a queue."""
    for process in processes:
        process.join(timeout=JOIN_TIMEOUT)

        if process.is_alive():
            process.terminate()
            process.join()


if __name__ == "__main__":
    main()
