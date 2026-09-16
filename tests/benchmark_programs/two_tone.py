"""
Two-tone qubit spectroscopy. Benchmark copy of programs/two_tone.py (program builder only).
"""

from __future__ import annotations

import numpy as np
import qm
import qm.qua as q

from . import utils as u
from .readout_spectoscopy import measure_readout


def two_tone_prog(
    *,
    num_inner: int,
    drive_frequencies_if: np.ndarray,
    drive_element_name: str,
    drive_pulse_name: str,
    readout_element_name: str,
    readout_pulse_name: str,
    drive_duration_cycles: int,
    drive_amplitude_rel: float = 1.0,
    readout_amplitude_rel: float = 0.0075,
    simultaneous: bool = True,
    drive_readout_wait_ns: int = 16,
    charge_dc: float = 0.0,
    remove_background: bool = False,
) -> qm.Program:
    """QUA: average ``num_inner`` shots over the drive-IF grid at fixed bias.

    Stream output ``I``/``Q`` averaged over the inner axis -> shape ``(n_freq, n_bg)``.
    When ``remove_background`` is True, each frequency is measured at
    ``drive_amplitude_rel`` then at zero drive amplitude (``n_bg=2``).
    """
    drive_frequencies_if = np.rint(drive_frequencies_if).astype(int)
    # print("drive_frequencies_if", drive_frequencies_if)
    n_freq = len(drive_frequencies_if)
    wait_c = round(drive_readout_wait_ns / 4) if drive_readout_wait_ns > 0 else 0
    bg_amplitudes = (
        [drive_amplitude_rel, 0.0] if remove_background else [drive_amplitude_rel]
    )
    n_bg = len(bg_amplitudes)
    print(
        f"drive_pulse_name = {drive_pulse_name}; drive_element_name = {drive_element_name}"
    )

    with q.program() as prog:  # type: ignore[var-annotated]
        avg_i = q.declare(int)
        f_if = q.declare(int)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)

        q.ramp_to_zero("flux_dc_0")
        q.ramp_to_zero("charge_dc_0")
        q.play("charge_dc_set" * q.amp(charge_dc), "charge_dc_0")

        q.update_frequency(drive_element_name, int(120e6))
        with q.for_each_(f_if, drive_frequencies_if.tolist()):
            # q.update_frequency(drive_element_name, f_if)
            # q.update_frequency(readout_element_name, f_if)
            # q.wait(100_000 // 4)  # 100 us
            for amp_rel in bg_amplitudes:
                with q.for_(avg_i, 0, avg_i < num_inner, avg_i + 1):  # type: ignore[operator]
                    q.align()
                    if simultaneous:
                        q.play(
                            drive_pulse_name * q.amp(amp_rel),
                            drive_element_name,
                            duration=drive_duration_cycles,
                        )
                        measure_readout(
                            readout_pulse_name=readout_pulse_name,
                            readout_amplitude_rel=readout_amplitude_rel,
                            readout_element_name=readout_element_name,
                            I_val=I_val,
                            Q_val=Q_val,
                        )
                    else:
                        q.play(
                            drive_pulse_name * q.amp(amp_rel),
                            drive_element_name,
                            duration=drive_duration_cycles,
                        )
                        q.align()
                        if wait_c > 0:
                            q.wait(wait_c, readout_element_name)
                        measure_readout(
                            readout_pulse_name=readout_pulse_name,
                            readout_amplitude_rel=readout_amplitude_rel,
                            readout_element_name=readout_element_name,
                            I_val=I_val,
                            Q_val=Q_val,
                        )
                    u.vars_save(I_val, Q_val)

        with q.stream_processing():
            I_val.st.buffer(n_freq, n_bg, num_inner).map(
                q.FUNCTIONS.average(axis=2)
            ).save("I")
            Q_val.st.buffer(n_freq, n_bg, num_inner).map(
                q.FUNCTIONS.average(axis=2)
            ).save("Q")

    return prog
