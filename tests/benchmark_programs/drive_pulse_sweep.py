"""
Drive pulse sweep. Benchmark copy of programs/drive_pulse_sweep.py (program builder only).
"""

from __future__ import annotations

import numpy as np
import qm
import qm.qua as q

from . import utils as u
from .flux_calibration_2p import flux_calibration_2p_action
from .readout_spectoscopy import measure_readout


def drive_pulse_sweep_prog(
    *,
    num_inner: int,
    num_outer: int,
    charge_dc: float,
    drive_durations_ns: np.ndarray,
    drive_frequencies_if: np.ndarray,
    charge_drive_amplitudes_rel: np.ndarray,
    charge_drive_pulse_name: str,
    charge_element_name: str,
    readout_pulse_name: str,
    readout_element_name: str,
    pre_drive_wait_ns: int = 100,
    post_drive_wait_ns: int = 100,
    readout_amplitude_rel: float = 1.0,
    flux_calibration_2p_config: dict | None = None,
) -> qm.Program:
    """QUA program: per rep, I/Q shape (n_f, n_amplitude, n_duration, pre/post); job stacks num_inner reps."""
    drive_durations_cycles = np.rint(drive_durations_ns / 4.0).astype(int)
    # print(drive_durations_cycles)
    drive_frequencies_if = np.rint(
        np.asarray(drive_frequencies_if, dtype=float)
    ).astype(int)
    # print("drive_frequencies_if", drive_frequencies_if)

    pre_c = round(pre_drive_wait_ns / 4) if pre_drive_wait_ns > 0 else 0
    post_c = round(post_drive_wait_ns / 4) if post_drive_wait_ns > 0 else 0

    with q.program() as prog:  # type: ignore[var-annotated]
        rep = q.declare(int)
        rep_outer = q.declare(int)

        f_if = q.declare(int)
        dur_c = q.declare(int)
        amp_rel = q.declare(float)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)
        correction_var = u.declare_qm_var(q.fixed)

        q.ramp_to_zero("flux_dc_0")
        q.ramp_to_zero("charge_dc_0")
        q.play("charge_dc_set" * q.amp(charge_dc), "charge_dc_0")

        if flux_calibration_2p_config is not None:
            with q.for_(rep_outer, 0, rep_outer < 10, rep_outer + 1):  # pyright: ignore[reportOperatorIssue]
                flux_calibration_2p_action(
                    correction_var=correction_var,
                    **flux_calibration_2p_config,
                )

        with q.for_(rep_outer, 0, rep_outer < num_outer, rep_outer + 1):  # pyright: ignore[reportOperatorIssue]
            if flux_calibration_2p_config is not None:
                flux_calibration_2p_action(
                    correction_var=correction_var,
                    **flux_calibration_2p_config,
                )
            with q.for_each_(f_if, drive_frequencies_if.tolist()):
                q.update_frequency(charge_element_name, f_if)
                with q.for_each_(amp_rel, charge_drive_amplitudes_rel.tolist()):
                    with q.for_each_(dur_c, drive_durations_cycles.tolist()):
                        with q.for_(rep, 0, rep < num_inner, rep + 1):  # type: ignore[operator]
                            q.align()
                            # q.wait(100_000 // 4)
                            q.align()
                            measure_readout(
                                readout_pulse_name=readout_pulse_name,
                                readout_amplitude_rel=readout_amplitude_rel,
                                readout_element_name=readout_element_name,
                                I_val=I_val,
                                Q_val=Q_val,
                            )
                            u.vars_save(I_val, Q_val)
                            q.align()
                            if pre_c > 0:
                                q.wait(pre_c, charge_element_name, readout_element_name)
                            q.play(
                                charge_drive_pulse_name * q.amp(amp_rel),
                                charge_element_name,
                                duration=dur_c,
                            )
                            q.align()
                            if post_c > 0:
                                q.wait(
                                    post_c, charge_element_name, readout_element_name
                                )
                            q.align()
                            measure_readout(
                                readout_pulse_name=readout_pulse_name,
                                readout_amplitude_rel=readout_amplitude_rel,
                                readout_element_name=readout_element_name,
                                I_val=I_val,
                                Q_val=Q_val,
                            )
                            u.vars_save(I_val, Q_val)

        with q.stream_processing():
            expected_shape = (
                num_outer,
                len(drive_frequencies_if),
                len(charge_drive_amplitudes_rel),
                len(drive_durations_cycles),
                num_inner,
                2,
            )
            I_val.st.buffer(*expected_shape).save_all("I")
            Q_val.st.buffer(*expected_shape).save_all("Q")

    return prog
