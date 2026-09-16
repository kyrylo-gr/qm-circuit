"""
Two-tone spectroscopy with a readout-frequency sweep. Benchmark copy of programs/two_tone_readout.py (program builder only).
"""

from __future__ import annotations

import numpy as np
import qm
import qm.qua as q

from . import utils as u
from .readout_spectoscopy import measure_readout


def two_tone_readout_prog(
    *,
    num_inner: int,
    drive_frequencies_if: np.ndarray,
    readout_frequencies_if: np.ndarray,
    drive_element_name: str,
    drive_pulse_name: str,
    readout_element_name: str,
    readout_pulse_name: str,
    drive_duration_cycles: int,
    drive_amplitude_rel: float = 1.0,
    readout_amplitude_rel: float = 0.0075,
    simultaneous: bool = True,
    drive_readout_wait_ns: float = 16,
    charge_dc: float = 0.0,
    remove_background: bool = False,
    save_all: bool = False,
) -> qm.Program:
    """QUA: per drive IF, sweep the readout IF and average ``num_inner`` sweeps.

    Stream output ``I``/``Q`` -> shape ``(n_drive, n_amp, n_readout)`` when
    ``save_all=False`` (averaged over the shot axis), or
    ``(n_drive, n_amp, num_inner, n_readout)`` when ``save_all=True``. When
    ``remove_background`` is True each drive frequency is measured at
    ``drive_amplitude_rel`` and then at zero drive amplitude (``n_amp=2``).
    """
    drive_frequencies_if = np.rint(drive_frequencies_if).astype(int)
    readout_frequencies_if = np.rint(readout_frequencies_if).astype(int)
    n_drive = int(drive_frequencies_if.size)
    n_readout = int(readout_frequencies_if.size)
    drive_readout_wait_cycles = round(drive_readout_wait_ns / 4) if drive_readout_wait_ns > 0 else 0
    drive_amplitudes_rel = (
        [drive_amplitude_rel, 0.0] if remove_background else [drive_amplitude_rel]
    )
    n_amp = len(drive_amplitudes_rel)

    with q.program() as prog:  # type: ignore[var-annotated]
        avg_i = q.declare(int)
        f_drive_if = q.declare(int)
        f_readout_if = q.declare(int)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)

        # Sticky DC elements are additive, so reset before applying absolute targets.
        q.ramp_to_zero("flux_dc_0")
        q.ramp_to_zero("charge_dc_0")
        q.play("charge_dc_set" * q.amp(charge_dc), "charge_dc_0")

        with q.for_each_(f_drive_if, drive_frequencies_if.tolist()):
            q.update_frequency(drive_element_name, f_drive_if)
            for amp_rel in drive_amplitudes_rel:
                with q.for_(avg_i, 0, avg_i < num_inner, avg_i + 1):  # type: ignore[operator]
                    with q.for_each_(f_readout_if, readout_frequencies_if.tolist()):
                        # Retune the resonator before aligning so the drive and the
                        # readout pulse still start together in simultaneous mode.
                        q.update_frequency(readout_element_name, f_readout_if)
                        q.align()
                        q.play(
                            drive_pulse_name * q.amp(amp_rel),
                            drive_element_name,
                            duration=drive_duration_cycles,
                        )
                        if simultaneous is False:
                            q.align()
                            if drive_readout_wait_cycles > 0:
                                q.wait(drive_readout_wait_cycles, readout_element_name)
                        else:
                            if drive_readout_wait_cycles > 0:
                                q.wait(drive_readout_wait_cycles, readout_element_name)
                        measure_readout(
                            readout_pulse_name=readout_pulse_name,
                            readout_amplitude_rel=readout_amplitude_rel,
                            readout_element_name=readout_element_name,
                            I_val=I_val,
                            Q_val=Q_val,
                        )
                        u.vars_save(I_val, Q_val)

        with q.stream_processing():
            for stream_val, stream_name in ((I_val, "I"), (Q_val, "Q")):
                pipeline = stream_val.st.buffer(n_drive, n_amp, num_inner, n_readout)
                if not save_all:
                    pipeline = pipeline.map(q.FUNCTIONS.average(axis=2))
                pipeline.save(stream_name)

    return prog
