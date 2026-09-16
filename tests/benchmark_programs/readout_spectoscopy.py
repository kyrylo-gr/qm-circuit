"""
Readout spectroscopy: sweep readout frequency and measure resonator response (I/Q).

Benchmark copy of programs/readout_spectoscopy.py: only ``measure_readout`` and
``readout_spectroscopy_prog`` are kept.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

import qm
import qm.qua as q
from . import utils as u


# Use explicit dual-demod labels wired in setup_qm.py.
READOUT_IW_KEYS = ("I_0", "I_1", "Q_0", "Q_1")


def measure_readout(
    *,
    readout_pulse_name: str,
    readout_element_name: str,
    readout_amplitude_rel: float | q.QuaVariableType = 1,  # type: ignore[name-defined]
    I_val: q.QuaVariableType,  # type: ignore[name-defined]
    Q_val: q.QuaVariableType,  # type: ignore[name-defined]
    frequency_if: int | None = None,
    timestamp_stream=None,
) -> None:
    """
    One dual-demod readout.

    ``timestamp_stream`` is passed straight to ``q.measure``: the OPX then reports the
    start time of every measurement in clock cycles. Any analysis that needs the shot
    period (the HMM, most obviously) should take it from these rather than adding up
    pulse lengths and waits, which ignores whatever the compiler inserts.
    """
    if frequency_if is not None:
        q.update_frequency(readout_element_name, frequency_if)

    iw_i_0, iw_i_1, iw_q_0, iw_q_1 = READOUT_IW_KEYS
    # Dual demod: I = I_0*out1 + I_1*out2, Q = Q_0*out1 + Q_1*out2
    q.measure(
        readout_pulse_name * q.amp(readout_amplitude_rel),  # pulse name
        readout_element_name,  # element name
        None,  # stream
        q.dual_demod.full(iw_i_0, "out1", iw_i_1, "out2", I_val),
        q.dual_demod.full(iw_q_0, "out1", iw_q_1, "out2", Q_val),
        timestamp_stream=timestamp_stream,
    )


def readout_spectroscopy_prog(
    *,
    num_outer: int = 1,
    num_inner: int,
    frequencies_if: np.ndarray,
    readout_element_name: str,
    readout_pulse_name: str,
    readout_amplitude_rel: float | np.ndarray | Iterable[float] = 1,
    flux_dc: float = 0.0,
    charge_dc: float = 0.0,
    delay_inter_ns: int | float = 0,
    # save_all: bool = False,
    average_inner: bool = True,
    average_innermost: bool = True,
    flatten_inner: bool | None = None,
    flatten_innermost: bool | None = None,
    num_premeasure: int = 0,
    num_postmeasure: int = 0,
    num_innermost: int = 1,
) -> qm.Program:

    assert num_premeasure == 0 and num_postmeasure == 0, (
        "num_premeasure and num_postmeasure are not supported anymore"
    )

    frequencies_if = np.rint(frequencies_if).astype(int)
    readout_amplitudes_rel = np.atleast_1d(np.asarray(readout_amplitude_rel, dtype=float))
    num_amplitudes = int(readout_amplitudes_rel.size)
    num_frequencies = int(frequencies_if.size)
    default_amplitude = float(readout_amplitudes_rel[0])
    # print(
    #     f"num_amplitudes: {num_amplitudes}, num_frequencies: {num_frequencies}, num_inner: {num_inner}"
    # )

    with q.program() as prog:  # type: ignore[var-annotated]
        num_outer_i = u.declare_qm_var(int)
        num_inner_i = u.declare_qm_var(int)
        num_innermost_i = u.declare_qm_var(int)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)

        current_f = q.declare(int)
        current_amp = q.declare(q.fixed)

        # Sticky DC elements are additive, so reset before applying absolute targets.
        q.ramp_to_zero("flux_dc_0")
        q.ramp_to_zero("charge_dc_0")
        q.play("flux_dc_set" * q.amp(flux_dc), "flux_dc_0")
        q.play("charge_dc_set" * q.amp(charge_dc), "charge_dc_0")

        # if num_premeasure > 0:
        #     with q.for_(num_outer_i, 0, num_outer_i < num_premeasure, num_outer_i + 1):  # type: ignore[operator]
        #         measure_readout(
        #             readout_pulse_name=readout_pulse_name,
        #             readout_amplitude_rel=0,  # readout_amplitude_rel,
        #             readout_element_name=readout_element_name,
        #             I_val=I_val,
        #             Q_val=Q_val,
        #         )

        with q.for_(num_outer_i, 0, num_outer_i < num_outer, num_outer_i + 1):  # type: ignore[operator]
            q.pause()

            with q.for_(num_inner_i, 0, num_inner_i < num_inner, num_inner_i + 1):  # type: ignore[operator]
                with q.for_each_(current_amp, readout_amplitudes_rel.tolist()):
                    with q.for_each_(current_f, frequencies_if.tolist()):
                        q.update_frequency(readout_element_name, current_f)
                        with q.for_(
                            num_innermost_i,  # type: ignore[operator]
                            0,
                            num_innermost_i < num_innermost,  # type: ignore[operator]
                            num_innermost_i + 1,  # type: ignore[operator]
                        ):
                            measure_readout(
                                readout_pulse_name=readout_pulse_name,
                                readout_amplitude_rel=current_amp,
                                readout_element_name=readout_element_name,
                                I_val=I_val,
                                Q_val=Q_val,
                            )
                            u.vars_save(I_val, Q_val)
                            if delay_inter_ns > 0:
                                q.wait(round(delay_inter_ns / 4), readout_element_name)

                num_inner_i.save()
            num_outer_i.save()

        # if num_postmeasure > 0:
        #     with q.for_(num_outer_i, 0, num_outer_i < num_postmeasure, num_outer_i + 1):  # type: ignore[operator]
        #         measure_readout(
        #             readout_pulse_name=readout_pulse_name,
        #             readout_amplitude_rel=default_amplitude,
        #             readout_element_name=readout_element_name,
        #             I_val=I_val,
        #             Q_val=Q_val,
        #         )

        with q.stream_processing():
            # if not specified, flatten if only one inner loop
            if flatten_inner is None:
                flatten_inner = (num_inner == 1) and average_inner
            # if not specified, flatten if only one innermost loop
            if flatten_innermost is None:
                flatten_innermost = (num_innermost == 1) and average_innermost

            loops = (
                ((num_outer,) if num_outer > 1 else ())
                # when num_outer == 1, there's no need to include the inner loop in the buffer, since it will be there
                # but this way data is return without waiting for the inner loop to finish
                + (() if flatten_inner or (num_outer == 1 and average_inner) else (num_inner,))
                + (num_amplitudes, num_frequencies)
                + (() if flatten_innermost else (num_innermost,))
            )
            # It's important to use average() for inner loop in order to avoid waiting for the inner loop to finish
            average_axis = ((-1,) if average_innermost and num_innermost > 1 else ()) + (
                ((1,) if num_outer > 1 else (None,)) if average_inner else ()
            )
            # print(
            #     f"loops: {loops}, average_axis: {average_axis}, flatten_inner: {flatten_inner}, flatten_innermost: {flatten_innermost}"
            # )
            for stream_val, stream_name in ((I_val, "I"), (Q_val, "Q")):
                if len(average_axis) == 0:  # i.e. save all data
                    # print("Saving all data")
                    assert num_outer > 1 or num_inner > 1, (
                        "Please double check what happens when num_outer == 1 and num_inner == 1, since it will return partial data"
                    )
                    stream_val.st.buffer(*loops[1:]).save_all(stream_name)
                    # stream_val.st.save_all(stream_name)
                else:
                    buffer = stream_val.st.buffer(*loops)
                    for axis in average_axis:
                        # print(f"{stream_name}: averaging axis: {axis}, loops: {loops}")
                        if axis is None:
                            # print("averaging first axis")
                            buffer = buffer.average()
                        elif axis < 0:
                            # print(f"averaging last axis: {len(loops) + axis}")
                            buffer = buffer.map(q.FUNCTIONS.average(axis=len(loops) + axis))
                        else:
                            # print(f"averaging axis: {axis}")
                            buffer = buffer.map(q.FUNCTIONS.average(axis=axis))
                    buffer.save(stream_name)

            if num_outer > 1:
                num_outer_i.st.save("n_outer")
            if num_inner > 1:
                num_inner_i.st.save("n_inner")

    return prog
