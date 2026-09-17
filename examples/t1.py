"""T1

Reset the qubit actively, excite it, wait a delay, read out: the decay of the excited population with delay gives T1.
The reset helper loops on its own readout, and its block still collapses to one box.
"""

import numpy as np
import qm.qua as q


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))


def active_reset(I, threshold):
    measure_readout(I)
    with q.while_(I > threshold):
        q.play("x180", "qubit")
        q.align("qubit", "resonator")
        measure_readout(I)
    q.align("qubit", "resonator")


def t1(delays, threshold, n_avg):
    with q.program() as prog:
        n = q.declare(int)
        tau = q.declare(int)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_avg, n + 1):
            with q.for_each_(tau, delays):
                active_reset(I, threshold)
                q.play("x180", "qubit")
                q.wait(tau, "qubit")
                q.align("qubit", "resonator")
                measure_readout(I)
    return prog


ARGS = dict(delays=np.geomspace(4, 40_000, 30).astype(int), threshold=0.002, n_avg=1000)
