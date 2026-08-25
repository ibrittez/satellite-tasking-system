"""Shared task fixtures. Not auto-discovered: a package's conftest.py must
import the ones it needs, so fixtures stay opt-in per test package."""

from pathlib import Path

import pytest

from sat_task_system.domain.models import Task

# Anchored to this file, not to the cwd: paths hold no matter where pytest runs.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@pytest.fixture
def spec_tasks() -> list[Task]:
    """The 4-task example from the exercise spec (known optimum: payoff 16)."""
    return [
        Task.create("high_res_capture",   10.0, (1, 5)),
        Task.create("sensor_maintenance",  1.0, (1, 2)),
        Task.create("comms_test",          5.0, (5, 6)),
        Task.create("fsck_disk_a",         2.0, (1, 6)),
    ]


@pytest.fixture
def spec_tasks_json() -> Path:
    """Path to the on-disk JSON holding the same 4 tasks as spec_tasks."""
    return DATA_DIR / "spec_tasks.json"


@pytest.fixture
def benchmark_tasks() -> list[Task]:
    """A larger, realistic task list (~50 tasks, 10 resources) for performance tests."""
    return [
        Task.create("telemetry_uhf_tx", 5.0, [1, 5]),
        Task.create("img_hires_pampa", 15.0, [3, 6, 8]),
        Task.create("img_multispectral_andes", 12.0, [4, 6, 8]),
        Task.create("sband_rx_gnss", 8.0, [2, 5]),
        Task.create("imu_calibration", 2.0, [7, 9]),
        Task.create("star_tracker_alignment", 6.0, [3, 7]),
        Task.create("battery_heater_cycle", 1.0, [10]),
        Task.create("xband_downlink_data", 20.0, [1, 6]),
        Task.create("obc_mem_scrub", 3.0, [5]),
        Task.create("eps_solar_mppt_test", 4.0, [10, 5]),
        Task.create("payload_fw_update", 18.0, [2, 5, 6]),
        Task.create("gnss_rtk_sync", 9.0, [2, 7]),
        Task.create("sar_scan_ocean", 25.0, [8, 9, 6]),
        Task.create("uhf_beacon_tx", 2.0, [1]),
        Task.create("fsck_nand_a", 7.0, [5, 6]),
        Task.create("thermal_cam_cal", 5.0, [4, 10]),
        Task.create("sband_tx_logs", 11.0, [2, 6]),
        Task.create("magnetorquer_actuation", 8.0, [7, 10]),
        Task.create("reaction_wheel_desat", 10.0, [7]),
        Task.create("img_hires_antarctica", 14.0, [3, 6, 8]),
        Task.create("flash_wear_leveling", 4.0, [5, 6]),
        Task.create("adcs_sensor_fusion", 16.0, [5, 7, 9]),
        Task.create("xband_carrier_test", 3.0, [1, 5]),
        Task.create("ir_scan_amazon", 13.0, [4, 6, 8]),
        Task.create("gnss_ephemeris_dl", 12.0, [2, 5, 6]),
        Task.create("ping_ground_station", 1.0, [1, 2]),
        Task.create("cpu_benchmark", 2.0, [5]),
        Task.create("power_budget_calc", 3.0, [5, 10]),
        Task.create("deploy_solar_panel", 50.0, [9, 10]),
        Task.create("safe_mode_toggle", 100.0, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        Task.create("gyro_bias_estimation", 7.0, [7, 4]),
        Task.create("fpga_bitstream_load", 22.0, [2, 5, 9]),
        Task.create("sun_sensor_adc_read", 4.0, [3, 10]),
        Task.create("lora_mesh_sync", 11.0, [1, 8]),
        Task.create("eps_latchup_reset", 35.0, [10]),
        Task.create("gnss_pps_jitter_test", 14.0, [2, 7]),
        Task.create("thermal_louver_open", 6.0, [4]),
        Task.create("cam_bayer_filter_cal", 9.0, [3, 8]),
        Task.create("canbus_telemetry_dump", 13.0, [5, 6]),
        Task.create("i2c_bus_recovery", 19.0, [5, 7]),
        Task.create("watchdog_kick_test", 2.0, [5]),
        Task.create("sram_ecc_scrub", 8.0, [5, 9]),
        Task.create("rx_lna_calibration", 17.0, [1, 2]),
        Task.create("tx_pa_temp_check", 5.0, [1, 4]),
        Task.create("deploy_antenna_uhf", 45.0, [1, 9, 10]),
        Task.create("pll_lock_verify", 12.0, [2, 6]),
        Task.create("rtc_drift_comp", 3.0, [5, 7]),
        Task.create("magnetometer_spin_cal", 21.0, [7, 9]),
        Task.create("payload_heater_on", 8.0, [4, 10]),
        Task.create("flash_bad_block_scan", 15.0, [5, 6, 8]),
    ]
