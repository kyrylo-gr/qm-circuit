---
hide:
  - navigation
  - toc
---

# Quantum Machines programs to circuit diagrams

**qm-circuit** draws a [QUA](https://docs.quantum-machines.co/latest/) program as a quantum-circuit diagram. It
draws one line per element and one box per pulse, labelled only with the values your code sets. Loops appear as
repeat signs. Each call to one of your helper functions stays a single block that you can expand. Everything runs
offline: no Quantum Machines server and no hardware configuration. Diagrams are drawn with matplotlib, so each one
is a standard `Figure`: save it as SVG, PNG or PDF, show it in a notebook, or put it in your reports like any other
plot.

```python
import qm_circuit as qc

fig = qc.draw(rabi, **ARGS)  # your program function and its arguments; returns a matplotlib Figure
```

Pick an example below. Switch **Expanded** on to open helper blocks.

<!-- viewer -->

[Get started](getting-started.md){ .md-button .md-button--primary } [Browse the gallery](gallery.md){ .md-button }
{: .qc-actions }
