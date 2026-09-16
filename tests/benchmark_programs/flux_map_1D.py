"""
Flux map 1D (QM sticky flux sweep).

Benchmark copy of programs/flux_map_1D.py: ``flux_map_1D_qm_prog`` is the QUA part
extracted from ``flux_map_1D_qm_acq`` (no job execution, no Yoko).
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import qm
import qm.qua as q

from . import utils as u
from .readout_spectoscopy import measure_readout

# Stand-ins for state.cfg / state lookups (plausible literal values).
RESONATOR_FREQUENCY_LO = 6.0e9  # state.cfg.resonator__frequency_lo (Hz)
YOKO_TO_QM_COEFF = 2.0  # state.cfg.yoko_to_qm_coeff
FLUX_COARSE_STEP = 0.1  # state.flux_voltage_to_coarse_voltage rounds to this step (V)
READOUT_ELEMENT_NAME = "resonator"  # state.get_qm_element_from_pulse_name(readout_pulse_name)
FLUX_ELEMENT_NAME = "flux_dc_0"  # state.get_qm_element_from_pulse_name("flux_dc_set")


def flux_map_1D_qm_prog(
    frequencies: np.ndarray | float | Iterable[float],
    voltages: np.ndarray | Iterable[float],
    num_avg: int,
    *,
    readout_pulse_name: str = "readout_long",
    readout_amplitude_rel: float = 0.0075,
    delay_qm_inter_ns: int = 16,
    delay_flux_settle_ns: int = 0,
    # save_all: bool = False,
) -> qm.Program:
    """
    QUA part of ``flux_map_1D_qm_acq`` (extracted): readout spectroscopy with QM sticky
    flux sweep inside one QUA program.
    """
    voltages = np.asarray(voltages, dtype=float)
    if isinstance(frequencies, (np.floating, np.integer, float, int)):
        frequencies = [frequencies]
    frequencies = np.asarray(frequencies, dtype=float)
    frequencies_if = np.rint(frequencies - RESONATOR_FREQUENCY_LO).astype(
        int
    )

    coarse_voltage = round(float(voltages[len(voltages) // 2]) / FLUX_COARSE_STEP) * FLUX_COARSE_STEP
    yoko_to_qm_coeff = float(YOKO_TO_QM_COEFF)
    voltages_qm = np.asarray(
        (voltages - coarse_voltage) * yoko_to_qm_coeff, dtype=float
    )
    deltas_qm = np.concatenate(
        (
            np.asarray([voltages_qm[0]], dtype=float),
            np.diff(voltages_qm),
        )
    )

    readout_element_name = READOUT_ELEMENT_NAME
    flux_element_name = FLUX_ELEMENT_NAME
    n_voltages = len(voltages)
    n_freqs = len(frequencies_if)

    with q.program() as prog:  # type: ignore[var-annotated]
        i_avg = q.declare(int)
        delta_qm = q.declare(q.fixed)
        current_f = q.declare(int)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)

        q.ramp_to_zero(flux_element_name)

        with q.for_each_(delta_qm, deltas_qm.tolist()):
            q.play("flux_dc_set" * q.amp(delta_qm), flux_element_name)
            if delay_flux_settle_ns > 0:
                q.wait(round(delay_flux_settle_ns / 4), flux_element_name)

            with q.for_(i_avg, 0, i_avg < num_avg, i_avg + 1):  # type: ignore[operator]
                with q.for_each_(current_f, frequencies_if.tolist()):
                    q.update_frequency(readout_element_name, current_f)
                    measure_readout(
                        readout_pulse_name=readout_pulse_name,
                        readout_amplitude_rel=readout_amplitude_rel,
                        readout_element_name=readout_element_name,
                        I_val=I_val,
                        Q_val=Q_val,
                    )
                    u.vars_save(I_val, Q_val)
                    if delay_qm_inter_ns > 0:
                        q.wait(round(delay_qm_inter_ns / 4), readout_element_name)

        q.ramp_to_zero(flux_element_name)

        with q.stream_processing():
            if False:  # save_all:
                I_val.st.buffer(num_avg, n_freqs).save_all("I")
                Q_val.st.buffer(num_avg, n_freqs).save_all("Q")
            else:
                I_val.st.buffer(n_voltages, num_avg, n_freqs).map(
                    q.FUNCTIONS.average(axis=1)
                ).save("I")
                Q_val.st.buffer(n_voltages, num_avg, n_freqs).map(
                    q.FUNCTIONS.average(axis=1)
                ).save("Q")

    return prog
