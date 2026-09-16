"""
Two-point in-program flux calibration.

Benchmark copy of programs/flux_calibration_2p.py: ``flux_calibration_2p_config`` reads
literal constants instead of ``state.cfg``; ``flux_calibration_2p_debug_continuous_prog``
is the QUA part extracted from ``flux_calibration_2p_debug_continuous_acq``.
"""

from __future__ import annotations

import qm
import qm.qua as q

from . import utils as u
from .readout_spectoscopy import measure_readout
from .utils.qm_utils import QuaVarWithStream

# Stand-ins for state.cfg / state lookups (plausible literal values).
FLUX_CALIBRATION_2P = {  # state.cfg.flux_calibration_2p
    "frequency": 6.02e9,
    "readout_pulse_name": "readout_long",
    "readout_amplitude_rel": 0.1,
    "n_avg": 100,
    "delta_flux_V": 1e-3,
    "delay_ns": 16,
    "parabola_a": -50.0,
}
RESONATOR_FREQUENCY_LO = 6.0e9  # state.cfg.resonator__frequency_lo (Hz)
YOKO_TO_QM_COEFF = 2.0  # state.cfg.yoko_to_qm_coeff
READOUT_ELEMENT_NAME = "resonator"  # state.get_qm_element_from_pulse_name(readout pulse)
FLUX_ELEMENT_NAME = "flux_dc_0"  # state.get_qm_element_from_pulse_name("flux_dc_set")


def flux_calibration_2p_config(
    state: object = None,
    *,
    readout_pulse_name: str | None = None,
    readout_amplitude_rel: float | None = None,
    frequency: float | None = None,
    n_avg: int | None = None,
    delta_flux_V: float | None = None,
    delay_ns: int | None = None,
) -> dict:

    cal = FLUX_CALIBRATION_2P
    frequency = frequency or cal["frequency"]
    readout_pulse_name = readout_pulse_name or cal["readout_pulse_name"]

    readout_element_name = READOUT_ELEMENT_NAME
    flux_set_pulse = "flux_dc_set"
    flux_element_name = FLUX_ELEMENT_NAME
    readout_amplitude_rel = readout_amplitude_rel or cal["readout_amplitude_rel"]
    readout_lo_hz = float(RESONATOR_FREQUENCY_LO)
    frequency_if = int(round(frequency - readout_lo_hz))
    n_avg = n_avg if n_avg is not None else cal["n_avg"]

    delta_flux_V = delta_flux_V or cal["delta_flux_V"]

    yoko_to_qm_coeff = float(YOKO_TO_QM_COEFF)
    delta_qm = delta_flux_V * yoko_to_qm_coeff
    delay_ns = delay_ns if delay_ns is not None else cal["delay_ns"]

    a_coeff = cal["parabola_a"]

    assert a_coeff != 0.0, "parabola_a is 0 — run parabola calibration first"
    correction_factor = yoko_to_qm_coeff / (4.0 * a_coeff * delta_flux_V) / 2

    return {
        "flux_set_pulse": flux_set_pulse,
        "flux_element_name": flux_element_name,
        "readout_pulse_name": readout_pulse_name,
        "readout_element_name": readout_element_name,
        "readout_amplitude_rel": readout_amplitude_rel,
        "frequency_if": frequency_if,
        "n_avg": n_avg,
        "delta_qm": delta_qm,
        "correction_factor": correction_factor,
        "delay_ns": delay_ns,
    }


def flux_calibration_2p_action(
    *,
    flux_set_pulse: str,
    flux_element_name: str,
    readout_pulse_name: str,
    readout_element_name: str,
    readout_amplitude_rel: float,
    frequency_if: int,
    n_avg: int,
    delta_qm: float,
    correction_factor: float,
    delay_ns: int,
    correction_var: QuaVarWithStream,
) -> QuaVarWithStream:
    """
    QUA fragment: measure at ±δV, compute correction, apply it, and stream the result.

    Called once inside a ``with q.program()`` block (typically within a loop).
    """

    I_val = q.declare(q.fixed)
    Q_val = q.declare(q.fixed)
    I_left_acc = q.declare(q.fixed)
    I_right_acc = q.declare(q.fixed)
    avg_i = q.declare(int)
    inv_n_avg = 1.0 / n_avg

    q.update_frequency(readout_element_name, frequency_if)

    q.play(flux_set_pulse * q.amp(-delta_qm), flux_element_name)
    if delay_ns > 0:
        q.wait(delay_ns // 4, flux_element_name)
    q.align()

    q.assign(I_left_acc, 0.0)
    with q.for_(avg_i, 0, avg_i < n_avg, avg_i + 1):  # type: ignore[operator]
        measure_readout(
            readout_pulse_name=readout_pulse_name,
            readout_amplitude_rel=readout_amplitude_rel,
            readout_element_name=readout_element_name,
            I_val=I_val,
            Q_val=Q_val,
        )
        q.assign(I_left_acc, I_left_acc + I_val * inv_n_avg)  # pyright: ignore[reportOperatorIssue]
        q.align()

    q.play(flux_set_pulse * q.amp(2.0 * delta_qm), flux_element_name)
    if delay_ns > 0:
        q.wait(delay_ns // 4, flux_element_name)
    q.align()

    q.assign(I_right_acc, 0.0)
    with q.for_(avg_i, 0, avg_i < n_avg, avg_i + 1):  # type: ignore[operator]
        measure_readout(
            readout_pulse_name=readout_pulse_name,
            readout_amplitude_rel=readout_amplitude_rel,
            readout_element_name=readout_element_name,
            I_val=I_val,
            Q_val=Q_val,
        )
        q.assign(I_right_acc, I_right_acc + I_val * inv_n_avg)  # pyright: ignore[reportOperatorIssue]

    q.align()
    q.play(flux_set_pulse * q.amp(-delta_qm), flux_element_name)

    q.assign(correction_var, correction_factor * (I_left_acc - I_right_acc))  # pyright: ignore[reportOperatorIssue]
    # q.assign(correction_var, I_left_acc)
    q.play(flux_set_pulse * q.amp(correction_var), flux_element_name)
    correction_var.save()
    return correction_var


def flux_calibration_2p_debug_continuous_prog(
    state: object = None,
    *,
    n_buffer: int = 100_000,
) -> qm.Program:
    """
    QUA part of ``flux_calibration_2p_debug_continuous_acq`` (extracted; no job execution).
    """

    flux_element_name = FLUX_ELEMENT_NAME  # state.get_qm_element_from_pulse_name("flux_dc_set")

    with q.program() as prog:  # type: ignore[var-annotated]
        loop_i = q.declare(int)
        correction_var = u.declare_qm_var(q.fixed)
        q.ramp_to_zero(flux_element_name)

        with q.for_(loop_i, 0, loop_i < n_buffer, loop_i + 1):  # type: ignore[operator]
            flux_calibration_2p_action(
                correction_var=correction_var,
                **flux_calibration_2p_config(state=state),
            )

        with q.stream_processing():
            correction_var.st.save_all("corrections")
            correction_var.st.timestamps().save_all("timestamps")

    return prog
