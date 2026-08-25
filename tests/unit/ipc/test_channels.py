from sat_task_system.ipc.channels import create_channels


def test_the_fleet_gets_one_uplink_each_plus_a_shared_downlink():
    """N addressed uplinks and a single merged downlink, all distinct queues."""
    channels = create_channels(3)

    assert len(channels.uplinks) == 3
    assert len({*channels.uplinks, channels.downlink}) == 4
