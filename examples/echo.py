"""Echo (CPMG)

Refocus dephasing with pi pulses between two pi/2 pulses; strict timing keeps the spacing exact. Back-to-back waits
merge into one box.
"""

import numpy as np
import qm.qua as q


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def echo(delays, n_pi, n_avg):
    with q.program() as prog:
        n = q.declare(int)
        tau = q.declare(int)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_avg, n + 1):
            with q.for_each_(tau, delays):
                with q.strict_timing_():
                    q.play("x90", "qubit")
                    for _ in range(n_pi):
                        q.wait(tau, "qubit")
                        q.play("y180", "qubit")
                        q.wait(tau, "qubit")
                    q.play("x90", "qubit")
                q.align("qubit", "resonator")
                measure_readout(I)
    return prog


ARGS = dict(delays=np.arange(4, 2000, 20), n_pi=2, n_avg=1000)
