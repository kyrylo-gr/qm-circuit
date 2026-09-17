"""Rabi

Sweep the drive amplitude and read the qubit out after every pulse. The readout is a helper function: expand its
block to see the pulses inside.
"""

import numpy as np
import qm.qua as q


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def rabi(amplitudes, n_avg):
    with q.program() as prog:
        n = q.declare(int)
        a = q.declare(q.fixed)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_avg, n + 1):
            with q.for_each_(a, amplitudes):
                q.play("x180" * q.amp(a), "qubit")
                q.align("qubit", "resonator")
                measure_readout(I)
    return prog


ARGS = dict(amplitudes=np.linspace(0, 1.5, 31), n_avg=1000)
