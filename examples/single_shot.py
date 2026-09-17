"""Single-shot readout

Prepare ground or excited in turn and record one readout per shot, for the I/Q blobs and the threshold.
"""

import qm.qua as q


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def single_shot(n_shots):
    with q.program() as prog:
        n = q.declare(int)
        excited = q.declare(bool)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_shots, n + 1):
            with q.for_each_(excited, [False, True]):
                with q.if_(excited):
                    q.play("x180", "qubit")
                q.align("qubit", "resonator")
                measure_readout(I)
    return prog


ARGS = dict(n_shots=5000)
