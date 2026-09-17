# Getting started

## Install

```bash
pip install git+https://github.com/kyrylo-gr/qm-circuit
```

Requirements: Python 3.12 or newer and `qm-qua` 1.4.x, which is installed automatically. qm-circuit reads private
`qm-qua` internals, so other `qm-qua` versions are not supported (see [How it works](how-it-works.md#compatibility)).

## Draw a program function

Pass the function that builds your program, followed by its arguments. `draw` runs the function, records the
program and returns a matplotlib `Figure`. For this program function:

<!-- rabi source -->

draw it with:

```python
import qm_circuit as qc

fig = qc.draw(rabi, **ARGS)
fig.savefig("rabi.svg")
```

qm-circuit uses matplotlib as its backend, so the result is a standard matplotlib `Figure`. Use it as you would any
other plot: `savefig` to any format matplotlib supports (SVG, PNG, PDF), and keep it in notebooks, scripts and
reports. In a notebook, the figure displays on its own. Useful options:

| Option | Effect |
|---|---|
| `expand=True` | Show what is inside each helper block instead of one collapsed box. |
| `title="..."` | Replace the default title (the function name). |
| `max_width=8` | Wrap top-level statements into rows at most 8 inches wide. |
| `style={...}` | Change sizes and colours; see [Customising diagrams](customising.md). |
| `show_saves=True` | Also draw `save` statements. |

## Draw a program built inside an experiment

Lab code often builds the program and runs it in the same function. `capture` stops that code as soon as the
program is built, before any job runs:

```python
with qc.capture() as cap:
    run_t1_experiment(qubit, n_avg=1000)  # stopped right after `q.program()` exits

fig = cap.draw(expand=True)
```

## Inspect the model

`model` returns the tree the diagram is drawn from. `format_model` prints it as text, which helps when checking
what the diagram will show:

```python
print(qc.format_model(qc.model(rabi, **ARGS)))
```

<!-- rabi model -->

## Next

- [Gallery](gallery.md): common experiments, collapsed and expanded.
- [API reference](reference.md): every argument.
