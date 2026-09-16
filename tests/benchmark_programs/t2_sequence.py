"""
T2 Ramsey on the charge drive. Benchmark copy of programs/t2_sequence.py (program builder only).
"""

from __future__ import annotations

import logging
from typing import cast

import qm
import qm.qua as q

from . import utils as u
from .flux_calibration_2p import flux_calibration_2p_action
from .readout_spectoscopy import measure_readout

LOGGER = logging.getLogger(__name__)  # stands in for ..state.LOGGER

_SAVE_TIME_BETWEEN_DRIVE__CYCLES = 64 // 4


def t2_sequence_prog(
    *,
    num_inner: int,
    num_outer: int,
    charge_dc: float,
    wait_cycles_list: list[int],
    phases_turns_list: list[float],
    pad_cycles_list: list[int],
    charge_element_name: str,
    charge_drive_pulse_name: str,
    readout_pulse_name: str,
    readout_element_name: str,
    f_pulse_hz_int: int,
    herald_to_drive_delay_cycles: int = 800 // 4,
    post_pulse_gap_cycles: int = 200 // 4,
    thermal_wait_cycles: int = 0,
    readout_amplitude_rel: float = 1.0,
    pi_half_amp_rel: float = 0.5,
    echo_num: int = 0,
    flux_calibration_2p_config: dict | None = None,
) -> qm.Program:
    """QUA: buffer shape ``(num_outer, n_wait, num_inner, 2)`` for I/Q (pre and post readout per shot).

    The shot geometry is the one validated in ``exp_programs/ramsey_run.py`` (iteration 5),
    and every interval the qubit state sees is INDEPENDENT of tau:

      herald readout -> wait(delay, PINNED) -> pi/2 -> wait(tau) -> Z(phi) -> pi/2
                     -> wait(gap, PINNED) -> post readout -> wait(pad = tau_max - tau)

    Three things here were wrong before 2026-09-14 and each one alone flattens the fringe:

    * **The herald-to-drive delay was 64 ns, hardcoded**, with no parameter to raise it.
      ``readout00`` is a 5 us pulse at amplitude 0.04, so the first pi/2 and the whole idle
      happened inside the resonator ringdown. Measured in the same loop (ramsey_run.py:407):
      a spurious excess of **+0.0041 at 500 ns delay, 0.0000 at 1000 ns** -- against a total
      fringe half-amplitude of only ~0.025. Hence ``herald_to_drive_delay_cycles`` defaults
      to 800 ns and is the single most important parameter in this function.
    * **The readout-to-readout spacing tracked tau**, so the repetition rate -- and with it
      the steady-state population -- drifted smoothly along the tau axis. Iteration 4 lost
      T2* to exactly this degeneracy (351 +- 73 ns -> 5000 ns at dchi2 = -0.4). ``pad_cycles_list``
      holds the spacing constant instead.
    * **The frame phase was built in QUA** as ``Cast.mul_fixed_by_int(4 * detuning * 1e-9, tau_c)``,
      a ``fixed`` with range [-8, 8) TURNS, so it silently overflowed once
      ``detuning_hz * tau_ns > 8e9`` (10 MHz x 900 ns = 9 turns already does). The phase is now
      computed in Python, wrapped to [-0.5, 0.5), and carried per point in the ``for_each_``
      tuple -- there is no detuning x tau bound left.

    ``reset_phase`` is deliberately absent and ``update_frequency`` is called once per job
    before either pulse: the element oscillator has to keep running in absolute time, because
    that continuous phase is what puts the residual ``f_01 - (LO + IF)`` into the fringe.
    """
    n_wait = len(wait_cycles_list)
    if n_wait < 1:
        raise ValueError("wait_cycles_list must be non-empty")
    if any(c < 4 for c in wait_cycles_list):
        raise ValueError("Each wait must be >= 4 clock cycles (16 ns): QUA's minimum wait")
    if len(phases_turns_list) != n_wait or len(pad_cycles_list) != n_wait:
        raise ValueError("phases_turns_list and pad_cycles_list must match wait_cycles_list")
    if any(c < 4 for c in pad_cycles_list):
        raise ValueError("Each pad must be >= 4 clock cycles (16 ns): QUA's minimum wait")
    if herald_to_drive_delay_cycles * 4 < 800:
        LOGGER.warning(
            f"herald-to-drive delay {herald_to_drive_delay_cycles * 4} ns is below the 800 ns "
            "photon-free bound measured on 2026-09-11 (excess +0.0041 at 500 ns, 0.0000 at "
            "1000 ns). The first pi/2 will land inside the readout ringdown."
        )

    with q.program() as prog:  # type: ignore[var-annotated]
        rep = q.declare(int)
        rep_outer = q.declare(int)
        tau_c = q.declare(int)
        phi_v = q.declare(q.fixed)
        pad_c = q.declare(int)
        I_val = u.declare_qm_var(q.fixed)
        Q_val = u.declare_qm_var(q.fixed)
        correction_var = u.declare_qm_var(q.fixed)

        q.ramp_to_zero("flux_dc_0")
        q.ramp_to_zero("charge_dc_0")
        q.play("charge_dc_set" * q.amp(charge_dc), "charge_dc_0")

        # ONE carrier for both pi/2 pulses, set once before either of them.
        q.update_frequency(charge_element_name, f_pulse_hz_int)

        if flux_calibration_2p_config is not None:
            with q.for_(rep_outer, 0, rep_outer < 10, rep_outer + 1):  # pyright: ignore[reportOperatorIssue]
                flux_calibration_2p_action(
                    correction_var=correction_var,
                    **flux_calibration_2p_config,
                )

        with q.for_(rep_outer, 0, rep_outer < num_outer, rep_outer + 1):  # pyright: ignore[reportOperatorIssue]
            if flux_calibration_2p_config is not None:
                flux_calibration_2p_action(
                    correction_var=correction_var,
                    **flux_calibration_2p_config,
                )
            with q.for_each_(
                (tau_c, phi_v, pad_c),
                (
                    cast(list, wait_cycles_list),
                    cast(list, phases_turns_list),
                    cast(list, pad_cycles_list),
                ),
            ):
                with q.for_(rep, 0, rep < num_inner, rep + 1):  # type: ignore[operator]
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

                    # --- the Ramsey body, all element-scoped so nothing re-aligns on tau ---
                    # This align is load-bearing: without it the charge element's timeline
                    # still sits at the top of the shot and the delay below would be counted
                    # from BEFORE the herald readout, i.e. the pi/2 would land inside it.
                    q.align()
                    q.reset_frame(charge_element_name)
                    q.wait(herald_to_drive_delay_cycles, charge_element_name)
                    q.play(
                        charge_drive_pulse_name * q.amp(pi_half_amp_rel),
                        charge_element_name,
                    )
                    q.wait(tau_c, charge_element_name)
                    for _ in range(echo_num):
                        q.play(charge_drive_pulse_name, charge_element_name)
                        q.wait(tau_c, charge_element_name)
                    if echo_num == 0:
                        q.frame_rotation_2pi(phi_v, charge_element_name)  # the ONLY detuning
                    q.play(
                        charge_drive_pulse_name * q.amp(pi_half_amp_rel),
                        charge_element_name,
                    )
                    q.wait(post_pulse_gap_cycles, charge_element_name)
                    q.align()

                    measure_readout(
                        readout_pulse_name=readout_pulse_name,
                        readout_amplitude_rel=readout_amplitude_rel,
                        readout_element_name=readout_element_name,
                        I_val=I_val,
                        Q_val=Q_val,
                    )
                    u.vars_save(I_val, Q_val)

                    # Holds the readout-to-readout spacing, hence the repetition rate and the
                    # steady-state population, independent of tau.
                    q.align()
                    q.wait(pad_c, readout_element_name, charge_element_name)

        with q.stream_processing():
            expected_shape = (num_outer, n_wait, num_inner, 2)
            I_val.st.buffer(*expected_shape).save_all("I")
            Q_val.st.buffer(*expected_shape).save_all("Q")

    return prog
