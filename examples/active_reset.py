"""Active reset

Put the qubit in a superposition, then measure it and flip it back until it reads ground, instead of waiting for it to relax.
"""

import qm.qua as q


def active_reset(threshold, n_shots):
    with q.program() as prog:
        n = q.declare(int)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_shots, n + 1):
            q.play("x90", "qubit")
            q.align("qubit", "resonator")
            q.measure("readout", "resonator", q.demod.full("cos", I))
            q.align("qubit", "resonator")
            with q.while_(I > threshold):
                q.play("x180", "qubit")
                q.align("qubit", "resonator")
                q.measure("readout", "resonator", q.demod.full("cos", I))
    return prog


ARGS = dict(threshold=0.002, n_shots=10_000)
