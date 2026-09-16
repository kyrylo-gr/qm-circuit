"""
Charge calibration (QM sticky charge sweep).

Benchmark copy of programs/charge_calibration.py: ``charge_calibration_qm_prog`` is the
QUA part extracted from ``charge_calibration_qm_acq`` (no fit, no job execution).
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import qm
import qm.qua as q

from . import utils as u
from .readout_spectoscopy import measure_readout

# Stand-ins for state.cfg / state lookups (plausible literal values).
RESONATOR_FREQUENCY_LO = 6.0e9  # state.cfg.resonator__frequency_lo (Hz)
READOUT_ELEMENT_NAME = "resonator"  # state.get_qm_element_from_pulse_name(readout_pulse_name)
CHARGE_ELEMENT_NAME = "charge_dc_0"  # state.get_qm_element_from_pulse_name("charge_dc_set")


def charge_calibration_qm_prog(
    *,
    calibration_type: Literal["coarse", "fine"],
    frequency: float,
    num_avg: int,
    readout_amplitude_rel: float,
    voltages: np.ndarray,
    readout_pulse_name: str,
    delay_ns: int,
) -> qm.Program:
    """QUA part of ``charge_calibration_qm_acq`` (extracted)."""
    assert calibration_type == "coarse"

    # current_voltage = state.get_charge_voltage()
    deltas_qm = np.concatenate((np.asarray([voltages[0]], dtype=float), np.diff(voltages)))

    readout_lo_hz = float(RESONATOR_FREQUENCY_LO)
    readout_if_hz = float(frequency - readout_lo_hz)
    frequency_if = int(round(readout_if_hz))

    readout_element_name = READOUT_ELEMENT_NAME
    charge_element_name = CHARGE_ELEMENT_NAME

    with q.program() as prog:  # type: ignore[var-annotated]
        i_avg = q.declare(int)
        delta_qm = q.declare(q.fixed)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)

        q.update_frequency(readout_element_name, frequency_if)
        q.ramp_to_zero(charge_element_name)

        with q.for_each_(delta_qm, deltas_qm.tolist()):
            q.play("charge_dc_set" * q.amp(delta_qm), charge_element_name)
            if delay_ns > 0:
                q.wait(round(delay_ns / 4), charge_element_name)
            q.align()
            with q.for_(i_avg, 0, i_avg < num_avg, i_avg + 1):  # type: ignore[operator]
                measure_readout(
                    readout_pulse_name=readout_pulse_name,
                    readout_amplitude_rel=readout_amplitude_rel,
                    readout_element_name=readout_element_name,
                    I_val=I_val,
                    Q_val=Q_val,
                )
                u.vars_save(I_val, Q_val)

        q.ramp_to_zero(charge_element_name)

        with q.stream_processing():
            I_val.st.buffer(num_avg).save_all("I")
            Q_val.st.buffer(num_avg).save_all("Q")

    return prog
