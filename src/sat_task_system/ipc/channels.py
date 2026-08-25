from dataclasses import dataclass

from multiprocessing import Queue as make_queue
from multiprocessing.queues import Queue

from sat_task_system.ipc.messages import ExecuteTasks, TaskExecuted


@dataclass(frozen=True)
class Channels:
    # one uplink per satellite, index == sat_id
    uplinks: tuple[Queue[ExecuteTasks], ...]

    # shared by all satellites
    downlink: Queue[TaskExecuted]


def create_channels(sat_count: int) -> Channels:
    uplinks: tuple[Queue[ExecuteTasks], ...] = tuple(
        make_queue() for _ in range(sat_count)
    )

    downlink: Queue[TaskExecuted] = make_queue()

    return Channels(uplinks, downlink)
