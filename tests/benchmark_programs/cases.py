"""Benchmark cases: (module, function name, sample kwargs) building a valid QUA program offline."""

from __future__ import annotations

import numpy as np

# Readout-element / pulse names used throughout (any string builds offline).
RO = dict(readout_pulse_name="readout00", readout_element_name="resonator")

FLUX_2P_CONFIG = dict(
    flux_set_pulse="flux_dc_set",
    flux_element_name="flux_dc_0",
    readout_pulse_name="readout_long",
    readout_element_name="resonator",
    readout_amplitude_rel=0.1,
    frequency_if=20_000_000,
    n_avg=4,
    delta_qm=0.002,
    correction_factor=-0.01,
    delay_ns=16,
)

CASES: dict[str, tuple[str, str, dict]] = {
    "readout_spectroscopy": (
        "readout_spectoscopy",
        "readout_spectroscopy_prog",
        dict(num_outer=2, num_inner=3, frequencies_if=np.array([10e6, 20e6, 30e6]),
             readout_element_name="resonator", readout_pulse_name="readout_long",
             readout_amplitude_rel=[0.1, 0.2], flux_dc=0.01, charge_dc=0.02, delay_inter_ns=100),
    ),
    "flux_calibration_2p_debug_continuous": (
        "flux_calibration_2p", "flux_calibration_2p_debug_continuous_prog", dict(n_buffer=5),
    ),
    "t1_sequence": (
        "t1_sequence",
        "t1_sequence_prog",
        dict(num_inner=5, num_outer=2, charge_dc=0.1, wait_cycles_list=[4, 16, 64],
             flux_calibration_2p_config=FLUX_2P_CONFIG, **RO),
    ),
    "t2_sequence": (
        "t2_sequence",
        "t2_sequence_prog",
        dict(num_inner=5, num_outer=2, charge_dc=0.1, wait_cycles_list=[4, 8, 16],
             phases_turns_list=[0.0, 0.1, 0.2], pad_cycles_list=[16, 12, 4],
             charge_element_name="charge_drive", charge_drive_pulse_name="charge_drive_qubit_pi_half",
             f_pulse_hz_int=50_000_000, echo_num=1, thermal_wait_cycles=100,
             flux_calibration_2p_config=FLUX_2P_CONFIG, **RO),
    ),
    "pi_pulse_check": (
        "pi_pulse_check",
        "pi_pulse_check_prog",
        dict(num_inner=5, num_outer=2, charge_dc=0.1, pulse_name="charge_drive_qubit_fast_pi",
             charge_element_name="charge_drive", frequency_if=20_000_000,
             flux_calibration_2p_config=FLUX_2P_CONFIG, **RO),
    ),
    "histogram_sequence": (
        "histogram_sequence",
        "histogram_sequence_prog",
        dict(num_outer=2, num_inner=5, readout_amplitude_rel=1.0, delay_ns=100, frequency_if=20_000_000,
             charge_dc=0.1, flux_calibration_2p_config=FLUX_2P_CONFIG,
             drive_element_name="charge_drive", drive_pulse_name="charge_drive_plasmon_normal",
             drive_duration_cycles=1250, **RO),
    ),
    "drive_pulse_sweep": (
        "drive_pulse_sweep",
        "drive_pulse_sweep_prog",
        dict(num_inner=5, num_outer=2, charge_dc=0.1, drive_durations_ns=np.array([16.0, 40.0]),
             drive_frequencies_if=np.array([50e6, 60e6]), charge_drive_amplitudes_rel=np.array([0.5, 1.0]),
             charge_drive_pulse_name="charge_drive_qubit", charge_element_name="charge_drive",
             flux_calibration_2p_config=FLUX_2P_CONFIG, **RO),
    ),
    "spectoscopy_spectrum": (
        "spectoscopy_spectrum",
        "spectoscopy_spectrum_prog",
        dict(num_shots=10, frequencies_if=np.array([10e6, 20e6]), readout_element_name="resonator",
             readout_pulse_name="readout_long", readout_amplitude_rel=0.5, delay_ns=16),
    ),
    "two_tone": (
        "two_tone",
        "two_tone_prog",
        dict(num_inner=10, drive_frequencies_if=np.array([100e6, 110e6, 120e6]), drive_element_name="charge_drive_plasmon",
             drive_pulse_name="charge_drive_plasmon_normal", readout_element_name="resonator",
             readout_pulse_name="readout_long", drive_duration_cycles=1250, simultaneous=False,
             charge_dc=0.1, remove_background=True),
    ),
    "two_tone_readout": (
        "two_tone_readout",
        "two_tone_readout_prog",
        dict(num_inner=10, drive_frequencies_if=np.array([100e6, 110e6]), readout_frequencies_if=np.array([10e6, 20e6]),
             drive_element_name="charge_drive_plasmon", drive_pulse_name="charge_drive_plasmon_normal",
             readout_element_name="resonator", readout_pulse_name="readout_long", drive_duration_cycles=1250,
             simultaneous=False, charge_dc=0.1, remove_background=True),
    ),
    "charge_calibration_qm": (
        "charge_calibration",
        "charge_calibration_qm_prog",
        dict(calibration_type="coarse", frequency=6.02e9, num_avg=10, readout_amplitude_rel=0.1,
             voltages=np.linspace(-0.05, 0.05, 5), readout_pulse_name="readout_long", delay_ns=100),
    ),
    "flux_map_1D_qm": (
        "flux_map_1D",
        "flux_map_1D_qm_prog",
        dict(frequencies=[6.01e9, 6.02e9], voltages=np.linspace(0.2, 0.3, 5), num_avg=10,
             readout_pulse_name="readout_long", delay_flux_settle_ns=100),
    ),
    "flux_calibration_anticrossing_qm": (
        "flux_calibration_anticrossing",
        "flux_calibration_anticrossing_qm_prog",
        dict(num_avg=10, frequency=6.02e9, relative_span=(0.001, 0.004), readout_amplitude_rel=0.1,
             delay_ns=100, num_premeasure=5, num_postmeasure=0, voltage_step=0.001,
             save_premeasure=True),
    ),
    "mixer_drive_optimize": (
        "mixer_optimize",
        "mixer_drive_optimize_prog",
        dict(drive_if_frequency=-200e6, mixer_correction_gain=0.02, mixer_correction_phase=0.01,
             output_offset_I=-0.01, output_offset_Q=0.004),
    ),
}
