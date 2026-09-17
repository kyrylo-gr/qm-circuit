"""Qubit spectroscopy vs flux

Step the DC flux bias with a sticky pulse, let it settle, and sweep a weak saturation tone on the qubit at each
bias. The sticky pulse holds its level, so the flux line is ramped back to zero once the sweep is done.
"""

import numpy as np
import qm.qua as q


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def qubit_spectroscopy(biases, frequencies_if):
    with q.program() as prog:
        dc = q.declare(q.fixed)
        f_if = q.declare(int)
        I = q.declare(q.fixed)
        with q.for_each_(dc, biases):
            q.play("bias" * q.amp(dc), "flux_dc")
            q.wait(2_500, "flux_dc")
            q.align("flux_dc", "qubit", "resonator")
            with q.for_each_(f_if, frequencies_if):
                q.update_frequency("qubit", f_if)
                q.play("saturation" * q.amp(0.1), "qubit", duration=25_000)
                q.align("qubit", "resonator")
                measure_readout(I)
        q.ramp_to_zero("flux_dc")
    return prog


ARGS = dict(biases=np.linspace(-0.2, 0.2, 21), frequencies_if=np.linspace(-100e6, 100e6, 201))
