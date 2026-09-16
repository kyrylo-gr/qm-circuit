"""
Charge-drive IQ mixer optimization.

Benchmark copy of programs/mixer_optimize.py: ``mixer_drive_optimize_prog`` is the QUA
part extracted from the nested ``_debug_drive_job`` closure inside
``mixer_drive_optimize_acq`` (no spectrum analyzer, no optimizer, no job execution).
"""

from __future__ import annotations

import numpy as np
import qm
import qm.qua as q

# Stand-in for state.get_qm_element_from_pulse_name(pulse_name).
DRIVE_ELEMENT_NAME = "charge_drive_plasmon"


def _mixer_correction_from_gain_phase(gain: float, phase: float) -> list[float]:
    """Stand-in for ``state.cfg._mixer_correction_from_gain_phase`` (standard IQ-imbalance matrix)."""
    c = np.cos(phase)
    s = np.sin(phase)
    n = 1 / ((1 - gain**2) * (2 * c**2 - 1))
    return [float(n * x) for x in ((1 - gain) * c, (1 + gain) * s, (1 - gain) * s, (1 + gain) * c)]


def mixer_drive_optimize_prog(
    *,
    drive_if_frequency: float,
    pulse_name: str = "charge_drive_plasmon_normal",
    drive_amplitude_rel: float = 0.3,
    drive_duration_ns: float = 500,
    mixer_correction_gain: float,
    mixer_correction_phase: float,
    output_offset_I: float,
    output_offset_Q: float,
) -> qm.Program:
    """QUA part of ``mixer_drive_optimize_acq`` / ``_debug_drive_job`` (extracted)."""
    elm = DRIVE_ELEMENT_NAME
    drive_duration_cycles = max(1, round(drive_duration_ns / 4))

    with q.program() as prog:  # type: ignore[var-annotated]
        q.update_correction(
            elm,
            *_mixer_correction_from_gain_phase(
                mixer_correction_gain, mixer_correction_phase
            ),
        )
        q.update_frequency(elm, int(round(drive_if_frequency)))
        q.set_dc_offset(elm, "I", output_offset_I)
        q.set_dc_offset(elm, "Q", output_offset_Q)
        with q.while_(True):
            q.play(
                pulse_name * q.amp(drive_amplitude_rel),
                elm,
                duration=drive_duration_cycles,
            )

    return prog
