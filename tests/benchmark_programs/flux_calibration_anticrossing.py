"""
Flux calibration on the anticrossing (QM sticky flux sweep).

Benchmark copy of programs/flux_calibration_anticrossing.py: ``flux_calibration_anticrossing_qm_prog``
is the QUA part extracted from ``flux_calibration_anticrossing_qm_acq`` (no fit, no job
execution). ``two_wing_voltage_table`` is kept because the program needs the voltage table.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Tuple

import numpy as np
import qm
import qm.qua as q

from . import utils as u
from .readout_spectoscopy import measure_readout

# Stand-ins for state.cfg / state lookups (plausible literal values).
RESONATOR_FREQUENCY_LO = 6.0e9  # state.cfg.resonator__frequency_lo (Hz)
YOKO_TO_QM_COEFF = 2.0  # state.cfg.yoko_to_qm_coeff
FLUX_PI_VOLTAGE = 0.237  # state.get_dynamic_config("flux__pi_voltage") (V)
FLUX_COARSE_STEP = 0.1  # state.flux_voltage_to_coarse_voltage rounds to this step (V)
READOUT_ELEMENT_NAME = "resonator"  # state.get_qm_element_from_pulse_name(readout_pulse_name)
FLUX_ELEMENT_NAME = "flux_dc_0"  # state.get_qm_element_from_pulse_name("flux_dc_set")


def two_wing_voltage_table(
    center_voltage: float,
    relative_span: Sequence[float],
    step: float,
    # coarse_rounding_step: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Left wing on ``[center - span[1], center - span[0])``, right wing mirrored about
    ``center``; ``relative_span`` is a positive ``(inner, outer)`` half-width pair.
    """
    v_lo = center_voltage - relative_span[1]
    v_hi = center_voltage - relative_span[0]
    left_wing = np.arange(v_lo, v_hi, step, dtype=float)[::-1]
    right_wing = 2 * center_voltage - left_wing[::-1]
    # right_wing = 2 * center_voltage - left_wing
    # print("left_wing", left_wing)
    # print("right_wing", right_wing)

    # coarse_left = float(
    #     round((v_lo + v_hi) / 2 / coarse_rounding_step) * coarse_rounding_step
    # )

    return (
        left_wing,
        right_wing,
        np.concatenate((left_wing, right_wing)),  # full voltage table
        # coarse_left,
        # 2 * center_voltage - coarse_left,  # symmetric about center
    )


def flux_calibration_anticrossing_qm_prog(
    *,
    num_avg: int,
    frequency: float,
    relative_span: Tuple[float, float],
    readout_amplitude_rel: float,
    delay_ns: int,
    num_premeasure: int,
    num_postmeasure: int,
    voltage_step: float,
    readout_pulse_name: str = "readout_long",
    save_all: bool = False,
    save_premeasure: bool = False,
) -> qm.Program:
    """
    QUA part of ``flux_calibration_anticrossing_qm_acq`` (extracted): sweep flux bias via
    sticky QM ``flux_dc`` output at a fixed readout frequency.
    """
    assert num_postmeasure == 0, "num_postmeasure is not implemented for QM version"
    del (
        num_postmeasure,
        # num_premeasure,
    )  # sweep is fully inside a single QUA program

    pi_volt_init = FLUX_PI_VOLTAGE
    pi_voltage_coarse = round(pi_volt_init / FLUX_COARSE_STEP) * FLUX_COARSE_STEP

    yoko_to_qm_coeff = float(YOKO_TO_QM_COEFF)

    left_wing, right_wing, dc_table = two_wing_voltage_table(
        pi_volt_init,
        relative_span,
        voltage_step,
    )

    # left_wing_rel_qm = np.asarray(
    #     (left_wing - pi_voltage_coarse) * yoko_to_qm_coeff, dtype=float
    # )
    # right_wing_rel_qm = np.asarray(
    #     (right_wing - pi_voltage_coarse) * yoko_to_qm_coeff, dtype=float
    # )
    dc_table_rel_qm = np.asarray(
        (dc_table - pi_voltage_coarse) * yoko_to_qm_coeff, dtype=float
    )
    # idx = np.arange(len(dc_table_rel_qm))
    # idx = np.where(idx % 2 == 0, idx // 2, len(dc_table_rel_qm) - 1 - idx // 2)
    # dc_table_rel_qm = dc_table_rel_qm[idx]
    # dc_table_rel_qm = dc_table_rel_qm[::-1]

    assert np.all(left_wing - pi_volt_init < 0), (
        f"left_wing - pi_voltage = {left_wing - pi_volt_init}"
    )
    assert np.all(right_wing - pi_volt_init > 0), (
        f"right_wing - pi_voltage = {right_wing - pi_volt_init}"
    )

    readout_lo_hz = float(RESONATOR_FREQUENCY_LO)
    readout_if_hz = float(frequency - readout_lo_hz)
    frequency_if = int(round(readout_if_hz))

    readout_element_name = READOUT_ELEMENT_NAME
    flux_element_name = FLUX_ELEMENT_NAME

    deltas_qm = np.concatenate(
        (
            np.asarray([dc_table_rel_qm[0]], dtype=float),
            np.diff(dc_table_rel_qm),
        )
    )

    with q.program() as prog:  # type: ignore[var-annotated]
        i_avg = q.declare(int)
        delta_qm = q.declare(q.fixed)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)
        if save_premeasure:
            I_val_premeasure = u.declare_qm_var(q.fixed)
            Q_val_premeasure = u.declare_qm_var(q.fixed)
        else:
            I_val_premeasure = Q_val_premeasure = None

        sub = q.declare(int)
        q.assign(sub, 0)

        q.update_frequency(readout_element_name, frequency_if)
        # q.ramp_to_zero(flux_element_name)

        if num_premeasure > 0:
            with q.for_(i_avg, 0, i_avg < num_premeasure, i_avg + 1):  # type: ignore[operator]
                with q.if_(sub == 4999):
                    q.assign(sub, 0)
                    q.wait(int(3e9 // 4))
                with q.else_():
                    q.assign(sub, sub + 1)  # type: ignore[operator]

                measure_readout(
                    readout_pulse_name=readout_pulse_name,
                    readout_amplitude_rel=readout_amplitude_rel
                    if save_premeasure
                    else 0,
                    readout_element_name=readout_element_name,
                    I_val=I_val if I_val_premeasure is None else I_val_premeasure,
                    Q_val=Q_val if Q_val_premeasure is None else Q_val_premeasure,
                )
                if save_premeasure:
                    u.vars_save(I_val_premeasure, Q_val_premeasure)
                # q.wait(100_000 // 4)
            q.align()

        q.align()
        # q.wait(100_000_000 // 4)
        # q.align()

        with q.for_each_(delta_qm, deltas_qm.tolist()):
            q.play("flux_dc_set" * q.amp(delta_qm), flux_element_name)
            if delay_ns > 0:
                q.wait(round(delay_ns / 4), flux_element_name)

            with q.for_(i_avg, 0, i_avg < num_avg, i_avg + 1):  # type: ignore[operator]
                measure_readout(
                    readout_pulse_name=readout_pulse_name,
                    readout_amplitude_rel=readout_amplitude_rel,
                    readout_element_name=readout_element_name,
                    I_val=I_val,
                    Q_val=Q_val,
                )
                u.vars_save(I_val, Q_val)

        q.ramp_to_zero(flux_element_name)

        with q.stream_processing():
            if save_all:
                I_val.st.buffer(len(dc_table_rel_qm), num_avg).save_all("I")
                Q_val.st.buffer(len(dc_table_rel_qm), num_avg).save_all("Q")
            else:
                I_val.st.buffer(len(dc_table_rel_qm), num_avg).map(
                    q.FUNCTIONS.average(axis=1)
                ).save("I")
                Q_val.st.buffer(len(dc_table_rel_qm), num_avg).map(
                    q.FUNCTIONS.average(axis=1)
                ).save("Q")
            if (
                save_premeasure
                and I_val_premeasure is not None
                and Q_val_premeasure is not None
            ):
                I_val_premeasure.st.save_all("I_premeasure")
                Q_val_premeasure.st.save_all("Q_premeasure")

    return prog
