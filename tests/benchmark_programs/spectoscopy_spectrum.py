"""
Spectroscopy spectrum. Benchmark copy of programs/spectoscopy_spectrum.py (program builder only).
"""

from __future__ import annotations

import numpy as np
import qm
import qm.qua as q

from . import utils as u
from .readout_spectoscopy import measure_readout


def spectoscopy_spectrum_prog(
    *,
    num_shots: int,
    frequencies_if: np.ndarray,
    readout_element_name: str,
    readout_pulse_name: str,
    readout_amplitude_rel: float = 1.0,
    delay_ns: int = 16,
) -> qm.Program:
    frequencies_if = np.rint(frequencies_if).astype(int)

    with q.program() as prog:  # type: ignore[var-annotated]
        shot_i = q.declare(int)
        current_f = q.declare(int)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)

        with q.for_(shot_i, 0, shot_i < num_shots, shot_i + 1):  # type: ignore[operator]
            with q.for_each_(current_f, frequencies_if.tolist()):
                q.update_frequency(readout_element_name, current_f)
                q.align()
                if delay_ns > 0:
                    q.wait(round(delay_ns / 4), readout_element_name)
                q.align()
                measure_readout(
                    readout_pulse_name=readout_pulse_name,
                    readout_amplitude_rel=readout_amplitude_rel,
                    readout_element_name=readout_element_name,
                    I_val=I_val,
                    Q_val=Q_val,
                )
                u.vars_save(I_val, Q_val)
                if delay_ns > 0:
                    q.wait(round(delay_ns / 4), readout_element_name)

        with q.stream_processing():
            I_val.st.buffer(len(frequencies_if)).save_all("I")
            Q_val.st.buffer(len(frequencies_if)).save_all("Q")
            I_val.st.timestamps().buffer(len(frequencies_if)).save_all("timestamps")

    return prog
