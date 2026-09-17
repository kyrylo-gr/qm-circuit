"""Rabi chevron

Sweep the drive frequency and the pulse duration; the excited population draws a chevron.
"""

import numpy as np
import qm.qua as q


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))
    q.wait(25_000)


def rabi_chevron(frequencies_if, max_duration):
    with q.program() as prog:
        f_if = q.declare(int)
        t = q.declare(int)
        I = q.declare(q.fixed)
        with q.for_each_(f_if, frequencies_if):
            q.update_frequency("qubit", f_if)
            with q.for_(t, 4, t < max_duration, t + 4):
                q.play("x180", "qubit", duration=t)
                q.align()
                measure_readout(I)
    return prog


ARGS = dict(frequencies_if=np.linspace(-20e6, 20e6, 41), max_duration=400)
