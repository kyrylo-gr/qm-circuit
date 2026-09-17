"""Pairwise CZ gates

Entangle three qubits pair by pair: q1-q2, then q1-q3, then q2-q3. Each gate is a helper function acting on two
lines; the q1-q3 block skips q2, so it is drawn as two boxes joined across it.
"""

import qm.qua as q


def cz(a, b):
    q.align(a, b)
    q.play("cz", a)
    q.play("cz", b)
    q.align(a, b)


def pairwise_cz(n_avg):
    with q.program() as prog:
        n = q.declare(int)
        with q.for_(n, 0, n < n_avg, n + 1):
            q.play("x90", "q1")
            q.play("x90", "q2")
            q.play("x90", "q3")
            cz("q1", "q2")
            cz("q1", "q3")
            cz("q2", "q3")
    return prog


ARGS = dict(n_avg=1000)
