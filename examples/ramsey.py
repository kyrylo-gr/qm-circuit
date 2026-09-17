"""Ramsey

Two pi/2 pulses around a swept wait, the second one phase-shifted to add a virtual detuning. The readout is a helper
function: expand its block to see the pulses inside.
"""

import numpy as np
import qm.qua as q


def measure_readout(I, amplitude=1.0):
    q.measure("readout" * q.amp(amplitude), "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def ramsey(delays, phases, n_avg):
    with q.program() as prog:
        n = q.declare(int)
        tau = q.declare(int)
        phi = q.declare(q.fixed)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_avg, n + 1):
            with q.for_each_((tau, phi), (delays, phases)):
                q.reset_frame("qubit")
                q.reset_if_phase("qubit")
                q.play("x90", "qubit")
                q.wait(tau, "qubit")
                q.frame_rotation_2pi(phi, "qubit")
                q.play("x90", "qubit")
                q.align("qubit", "resonator")
                measure_readout(I, amplitude=0.5)
    return prog


ARGS = dict(delays=np.arange(4, 400, 8), phases=np.arange(0, 50) * 0.08 % 1, n_avg=1000)
