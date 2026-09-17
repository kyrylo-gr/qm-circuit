"""Customising diagrams

One program drawn four ways: default style, larger font, custom colours, and wrapped into rows.
"""

import qm.qua as q

import qm_circuit as qc


# --8<-- [start:program]
def measure_readout(I, amplitude=1.0):
    q.measure("readout" * q.amp(amplitude), "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def hahn_echo(tau):
    with q.program() as prog:
        I = q.declare(q.fixed)
        q.play("x90", "qubit")
        q.wait(tau, "qubit")
        q.play("x180", "qubit")
        q.wait(tau, "qubit")
        q.play("x90", "qubit")
        q.align("qubit", "resonator")
        measure_readout(I, amplitude=0.5)
    return prog
# --8<-- [end:program]


# --8<-- [start:default]
default = qc.draw(hahn_echo, tau=400)
# --8<-- [end:default]

# --8<-- [start:larger_font]
larger_font = qc.draw(hahn_echo, tau=400, style={"size": 11})
# --8<-- [end:larger_font]

# --8<-- [start:custom_colours]
custom_colours = qc.draw(hahn_echo, tau=400, style={"colors": {"pulse": "#0b5394", "measure": "#b8860b"}})
# --8<-- [end:custom_colours]

# --8<-- [start:wrapped]
wrapped = qc.draw(hahn_echo, tau=400, expand=True, max_width=6)
# --8<-- [end:wrapped]
