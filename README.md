# **qm-circuit**: Quantum Machines programs to circuit diagrams.

[![CI](https://github.com/kyrylo-gr/qm-circuit/actions/workflows/ci.yml/badge.svg)](https://github.com/kyrylo-gr/qm-circuit/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/qm-circuit)](https://pypi.org/project/qm-circuit/)
[![Python](https://img.shields.io/pypi/pyversions/qm-circuit)](https://pypi.org/project/qm-circuit/)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://kyrylo-gr.github.io/qm-circuit/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/kyrylo-gr/qm-circuit/blob/main/LICENSE)
[![CodeFactor](https://www.codefactor.io/repository/github/kyrylo-gr/qm-circuit/badge)](https://www.codefactor.io/repository/github/kyrylo-gr/qm-circuit)



### What
qm-circuit draws a [QUA](https://docs.quantum-machines.co/latest/) program as a quantum-circuit diagram: one line
per element, one box per pulse, labelled only with the values your code sets. Loops appear as repeat signs, and each
call to one of your helper functions stays a single block that you can expand.

### Why

It isn't meant to compete with the Quantum Machines simulator. It lays out your whole sequence in order, so one look
is enough to follow the program or spot a mistake, without digging through the code.

### How

- **Offline**: no Quantum Machines server, no hardware configuration.
- **Plain matplotlib**: every diagram is a `Figure`. Save it as SVG, PNG or PDF, or show it in a notebook.
- **Fully customisable style**: sizes, colours, fonts and spacing are all set through `style=`. See
  [Customising diagrams](https://kyrylo-gr.github.io/qm-circuit/customising/).

## Install

```bash
pip install qm-circuit
```

Or install the latest version from source:

```bash
pip install git+https://github.com/kyrylo-gr/qm-circuit
```

For development, clone the repository and install it in editable mode:

```bash
git clone https://github.com/kyrylo-gr/qm-circuit
cd qm-circuit
pip install -e ".[test]"
```

Requires Python 3.12+ and `qm-qua` 1.3 or newer.

## Usage

```python
import numpy as np
import qm.qua as q
import qm_circuit as qc


def rabi(amplitudes, n_avg):
    with q.program() as prog:
        n = q.declare(int)
        a = q.declare(q.fixed)
        with q.for_(n, 0, n < n_avg, n + 1):
            with q.for_each_(a, amplitudes):
                q.play("x180" * q.amp(a), "qubit")
                q.align("qubit", "resonator")
                q.measure("readout", "resonator")
    return prog


fig = qc.draw(rabi, amplitudes=np.linspace(0, 1.5, 31), n_avg=1000)
fig.savefig("rabi.svg")
```

Program built inside an experiment function? `capture` stops it right after the program is built, before any job
runs:

```python
with qc.capture() as cap:
    run_t1_experiment(qubit, n_avg=1000)

fig = cap.draw(expand=True)
```

## Examples

Source code for each is in [`examples/`](https://github.com/kyrylo-gr/qm-circuit/tree/main/examples). More in the
[gallery](https://kyrylo-gr.github.io/qm-circuit/gallery/).

**Rabi**

![Rabi diagram](https://kyrylo-gr.github.io/qm-circuit/diagrams/rabi.svg)

```python
import numpy as np
import qm.qua as q
import qm_circuit as qc


def measure_readout(I):
    q.measure("readout", "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def rabi(amplitudes, n_avg):
    with q.program() as prog:
        n = q.declare(int)
        a = q.declare(q.fixed)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_avg, n + 1):
            with q.for_each_(a, amplitudes):
                q.play("x180" * q.amp(a), "qubit")
                q.align("qubit", "resonator")
                measure_readout(I)
    return prog


ARGS = dict(amplitudes=np.linspace(0, 1.5, 31), n_avg=1000)

fig = qc.draw(rabi, **ARGS)
fig.savefig("rabi.svg")
```

**Active reset**

![Active reset diagram](https://kyrylo-gr.github.io/qm-circuit/diagrams/active_reset.svg)

```python
import qm.qua as q
import qm_circuit as qc


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

fig = qc.draw(active_reset, **ARGS)
fig.savefig("active_reset.svg")
```

**Ramsey**

![Ramsey diagram](https://kyrylo-gr.github.io/qm-circuit/diagrams/ramsey.svg)

```python
import numpy as np
import qm.qua as q
import qm_circuit as qc


def measure_readout(I, amplitude=1.0):
    q.measure("readout" * q.amp(amplitude), "resonator", q.demod.full("cos", I))
    q.wait(25_000, "resonator")


def ramsey(delays, phases, n_avg):
    with q.program() as prog:
        n = q.declare(int)
        tau = q.declare(int)
        phi = q.declare(q.fixed)
        I = q.declare(q.fixed)
        with q.for_(n, 0, n < n_avg, n + 1):
            with q.for_each_((tau, phi), (delays, phases)):
                q.reset_frame("qubit")
                q.reset_if_phase("qubit")
                q.play("x90", "qubit")
                q.wait(tau, "qubit")
                q.frame_rotation_2pi(phi, "qubit")
                q.play("x90", "qubit")
                q.align("qubit", "resonator")
                measure_readout(I, amplitude=0.5)
    return prog


ARGS = dict(delays=np.arange(4, 400, 8), phases=np.arange(0, 50) * 0.08 % 1, n_avg=1000)

fig = qc.draw(ramsey, **ARGS)
fig.savefig("ramsey.svg")
```

## Documentation

Full guide, gallery and API reference: **<https://kyrylo-gr.github.io/qm-circuit/>**
