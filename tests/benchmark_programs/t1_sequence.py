"""
T1 by measure - wait - measure. Benchmark copy of programs/t1_sequence.py (program builder only).
"""

from __future__ import annotations

from typing import cast

import qm
import qm.qua as q

from . import utils as u
from .flux_calibration_2p import flux_calibration_2p_action
from .readout_spectoscopy import measure_readout


def t1_sequence_prog(
    *,
    num_inner: int,
    num_outer: int,
    charge_dc: float,
    wait_cycles_list: list[int],
    readout_pulse_name: str,
    readout_element_name: str,
    readout_amplitude_rel: float = 1.0,
    inter_readout_wait_cycles: int = 64 // 4,
    flux_calibration_2p_config: dict | None = None,
) -> qm.Program:
    """QUA: I/Q buffered as ``(num_outer, n_wait, num_inner, pre/post)``."""
    n_wait = len(wait_cycles_list)
    if n_wait < 1:
        raise ValueError("wait_cycles_list must be non-empty")
    if any(c < 4 for c in wait_cycles_list):
        raise ValueError("Each wait must be >= 4 clock cycles (16 ns)")

    with q.program() as prog:  # type: ignore[var-annotated]
        rep = q.declare(int)
        rep_outer = q.declare(int)
        tau_c = q.declare(int)
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
            with q.for_each_(tau_c, cast(list, wait_cycles_list)):
                with q.for_(rep, 0, rep < num_inner, rep + 1):  # type: ignore[operator]
                    q.align()
                    # preparation readout: whatever it says is the state we start from
                    measure_readout(
                        readout_pulse_name=readout_pulse_name,
                        readout_amplitude_rel=readout_amplitude_rel,
                        readout_element_name=readout_element_name,
                        I_val=I_val,
                        Q_val=Q_val,
                    )
                    u.vars_save(I_val, Q_val)
                    q.align()
                    q.wait(tau_c, readout_element_name)
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
                    if inter_readout_wait_cycles > 0:
                        q.wait(inter_readout_wait_cycles, readout_element_name)

        with q.stream_processing():
            expected_shape = (num_outer, n_wait, num_inner, 2)
            I_val.st.buffer(*expected_shape).save_all("I")
            Q_val.st.buffer(*expected_shape).save_all("Q")

    return prog
