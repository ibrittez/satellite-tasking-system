"""Starting the fleet, tearing it down, and running one batch to completion."""

from collections.abc import Sequence
from multiprocessing import Process

from sat_task_system.config import Config
from sat_task_system.domain.models import Summary, Task
from sat_task_system.ipc.channels import Channels, create_channels
from sat_task_system.loaders.in_memory_task_source import InMemoryTaskSource
from sat_task_system.ports.reporter import Reporter
from sat_task_system.processes.ground_station import GroundStation
from sat_task_system.processes.satellite import Satellite
from sat_task_system.reporting.capturing_reporter import CapturingReporter
from sat_task_system.reporting.multi_reporter import MultiReporter

# =======================================
# processes
# =======================================


def satellite_processes(failure_rates: Sequence[float],
                        channels: Channels) -> list[Process]:
    """One process per satellite, each holding its own uplink, its own failure
    rate and the shared downlink."""
    # One rate per satellite is a Config invariant, so enumerate covers the fleet.
    satellites = [
        Satellite(
            sat_id,
            failure_rate,
            channels.uplinks[sat_id],
            channels.downlink
        )
        for sat_id, failure_rate in enumerate(failure_rates)
    ]

    return [Process(target=satellite.run, name=f"satellite-{sat_id}")
            for sat_id, satellite in enumerate(satellites)]


def shutdown(processes: Sequence[Process], timeout: float) -> None:
    """Wait for a clean exit, then kill whatever is still blocked on a queue."""
    for process in processes:
        process.join(timeout=timeout)

        if process.is_alive():
            process.terminate()
            process.join()


# =======================================
# one batch, station included
# =======================================


def run_batch(tasks: list[Task],
              config: Config,
              reporters: Sequence[Reporter] = ()) -> Summary:
    """Plan, dispatch and collect one batch, and return what it produced.

    The station runs here, in the caller's process, which is what makes the
    summary readable on return: a Reporter publishing inside a child process
    could not hand it back. The satellites are still processes of their own, so
    the fleet is the same one the cli mode drives.

    Any reporter passed in is published to as well, after the capture, so a
    caller that needs the summary back does not give up the port to get it.
    """
    channels = create_channels(config.sat_count)
    satellites = satellite_processes(config.failure_rates, channels)

    capture = CapturingReporter()
    station = GroundStation(source=InMemoryTaskSource(tasks),
                            reporter=MultiReporter((capture, *reporters)),
                            collect_timeout=config.collect_timeout,
                            channels=channels,
                            sat_count=config.sat_count)

    for process in satellites:
        process.start()

    # Even if the station raises, no satellite is left behind waiting on a queue.
    try:
        station.run()
    finally:
        shutdown(satellites, config.join_timeout)

    return capture.summary
