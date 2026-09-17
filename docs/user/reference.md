# API reference

## Drawing

::: qm_circuit.draw

::: qm_circuit.capture
    options:
      members: [model, draw]
      show_bases: false

::: qm_circuit.model

::: qm_circuit.format_model

## Model

`model()` and `capture().model()` return a [`Program`][qm_circuit.Program], a tree of the classes below.

::: qm_circuit.Program
    options:
      show_source: false

::: qm_circuit.Play
    options:
      show_source: false

::: qm_circuit.Wait
    options:
      show_source: false

::: qm_circuit.Align
    options:
      show_source: false

::: qm_circuit.Op
    options:
      show_source: false

::: qm_circuit.Loop
    options:
      show_source: false

::: qm_circuit.If
    options:
      show_source: false

::: qm_circuit.Branch
    options:
      show_source: false

::: qm_circuit.Block
    options:
      show_source: false
