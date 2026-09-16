"""
Pi-pulse check: readout — conditional drive pulse — readout. Benchmark copy of programs/pi_pulse_check.py (program builder only).
"""

from __future__ import annotations

import qm
import qm.qua as q

from . import utils as u
from .flux_calibration_2p import flux_calibration_2p_action
from .readout_spectoscopy import measure_readout


_PI_ON_VALUES: tuple[bool, bool] = (False, True)


def pi_pulse_check_prog(
    *,
    num_inner: int,
    num_outer: int,
    charge_dc: float,
    pulse_name: str,
    charge_element_name: str,
    readout_pulse_name: str,
    readout_element_name: str,
    thermal_wait_cycles: int = 100_000 // 4,
    readout_amplitude_rel: float = 1.0,
    flux_calibration_2p_config: dict | None = None,
    frequency_if: int | None = None,
) -> qm.Program:
    """QUA: buffer shape ``(num_outer, num_inner, 2, 2)`` — (repeat, reps, bool_off_on, pre_post)."""
    with q.program() as prog:  # type: ignore[var-annotated]
        rep = q.declare(int)
        rep_outer = q.declare(int)
        pi_on = q.declare(bool)
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

        if frequency_if is not None:
            q.update_frequency(readout_element_name, frequency_if)

        with q.for_(rep_outer, 0, rep_outer < num_outer, rep_outer + 1):  # pyright: ignore[reportOperatorIssue]
            if flux_calibration_2p_config is not None:
                flux_calibration_2p_action(
                    correction_var=correction_var,
                    **flux_calibration_2p_config,
                )
            with q.for_(rep, 0, rep < num_inner, rep + 1):  # type: ignore[operator]
                with q.for_each_(pi_on, _PI_ON_VALUES):
                    q.align()
                    if thermal_wait_cycles > 0:
                        q.wait(thermal_wait_cycles)
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
                    with q.if_(pi_on):
                        q.play(pulse_name, charge_element_name)
                    with q.else_():
                        q.play(pulse_name * q.amp(0), charge_element_name)
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
            expected_shape = (num_outer, num_inner, 2, 2)
            I_val.st.buffer(*expected_shape).save_all("I")
            Q_val.st.buffer(*expected_shape).save_all("Q")

    return prog
