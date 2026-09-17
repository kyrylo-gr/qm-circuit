"""Resonator vs flux

Pause at each flux point so the host can set an external bias, then sweep the readout frequency.
"""

import numpy as np
import qm.qua as q


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def flux_map(n_flux, frequencies_if):
    with q.program() as prog:
        i = q.declare(int)
        f_if = q.declare(int)
        I = q.declare(q.fixed)
        with q.for_(i, 0, i < n_flux, i + 1):
            q.pause()
            with q.for_each_(f_if, frequencies_if):
                q.update_frequency("resonator", f_if)
                measure_readout(I)
    return prog


ARGS = dict(n_flux=21, frequencies_if=np.linspace(-50e6, 50e6, 101))
