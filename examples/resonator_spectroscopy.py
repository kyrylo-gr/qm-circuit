"""Resonator spectroscopy

Sweep the readout frequency and measure the resonator at each point.
"""

import numpy as np
import qm.qua as q


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def resonator_spectroscopy(frequencies_if, n_avg):
    with q.program() as prog:
        n = q.declare(int)
        f_if = q.declare(int)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_avg, n + 1):
            with q.for_each_(f_if, frequencies_if):
                q.update_frequency("resonator", f_if)
                measure_readout(I)
    return prog


ARGS = dict(frequencies_if=np.linspace(-50e6, 50e6, 101), n_avg=1000)
