"""
Repeated single-shot readout histogram. Benchmark copy of programs/histogram_sequence.py (program builder only).
"""

from __future__ import annotations

import qm
import qm.qua as q

from . import utils as u
from .readout_spectoscopy import measure_readout
from .flux_calibration_2p import flux_calibration_2p_action


def histogram_sequence_prog(
    *,
    num_outer: int,
    num_inner: int,
    readout_element_name: str,
    readout_pulse_name: str,
    readout_amplitude_rel: float,
    delay_ns: int,
    frequency_if: int | None = None,
    flux_dc: float = 0.0,
    charge_dc: float = 0.0,
    flux_calibration_2p_config: dict | None = None,
    save_timestamps: bool = True,
    drive_element_name: str | None = None,
    drive_pulse_name: str | None = None,
    drive_amplitude_rel: float = 1.0,
    drive_duration_cycles: int | None = None,
) -> qm.Program:
    """Repeated single-shot readout, optionally with an OPX tone playing over it.

    ``drive_element_name`` / ``drive_pulse_name`` add a drive that covers each
    shot: one play per shot on a different element, started at the same instant
    as the readout and lasting ``drive_duration_cycles``. The OPX oscillator is
    free-running, so back-to-back plays are phase continuous and this is a CW
    tone with a short gap where the loop's ``align`` sits. The drive frequency is
    deliberately NOT written here: leave it to ``set_intermediate_frequency`` on
    the machine so a frequency sweep can reuse one compiled program (compiling
    costs 6 s, running costs 1 s).
    """
    # print(f"flux_dc = {flux_dc:.2e} V")
    # print(f"charge_dc = {charge_dc:.2e} V")
    if (drive_element_name is None) != (drive_pulse_name is None):
        raise ValueError("drive_element_name and drive_pulse_name go together")
    if drive_element_name is not None and drive_duration_cycles is None:
        raise ValueError("drive_duration_cycles is required with a drive element")
    with q.program() as prog:  # type: ignore[var-annotated]
        shot_idx = q.declare(int)
        loop_i = q.declare(int)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)
        correction_var = u.declare_qm_var(q.fixed)
        # start time of every readout, in clock cycles, straight from the OPX. The
        # shot period is what T1 scales with, so it is measured, not added up.
        ts_stream = q.declare_stream() if save_timestamps else None

        if frequency_if is not None:
            q.update_frequency(readout_element_name, frequency_if)

        q.align()
        q.ramp_to_zero("flux_dc_0")
        q.ramp_to_zero("charge_dc_0")
        # q.play("flux_dc_set" * q.amp(flux_dc), "flux_dc_0")
        q.play("charge_dc_set" * q.amp(charge_dc), "charge_dc_0")

        with q.for_(loop_i, 0, loop_i < num_outer, loop_i + 1):  # type: ignore[operator]
            if flux_calibration_2p_config is not None:
                flux_calibration_2p_action(
                    correction_var=correction_var,
                    **flux_calibration_2p_config,
                )
            with q.for_(shot_idx, 0, shot_idx < num_inner, shot_idx + 1):  # type: ignore[operator]
                if drive_element_name is not None:
                    q.play(
                        drive_pulse_name * q.amp(drive_amplitude_rel),  # type: ignore[operator]
                        drive_element_name,
                        duration=int(drive_duration_cycles),  # type: ignore[arg-type]
                    )
                measure_readout(
                    readout_pulse_name=readout_pulse_name,
                    readout_amplitude_rel=readout_amplitude_rel,
                    readout_element_name=readout_element_name,
                    I_val=I_val,
                    Q_val=Q_val,
                    timestamp_stream=ts_stream,
                )
                q.align()
                if delay_ns > 0:
                    q.wait(round(delay_ns / 4), readout_element_name)
                u.vars_save(I_val, Q_val)
                q.align()

        with q.stream_processing():
            I_val.st.save_all("I")
            Q_val.st.save_all("Q")
            if ts_stream is not None:
                ts_stream.save_all("timestamps")
            if flux_calibration_2p_config is not None:
                correction_var.st.save_all("flux_corrections")

    return prog
