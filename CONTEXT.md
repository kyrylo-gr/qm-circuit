# QM circuit diagrams

Drawing a QUA program, built offline with `qm-qua`, as a schematic quantum-circuit
diagram that keeps the structure the physicist wrote.

## Language

### Programs

**QUA program**:
The protobuf program a `with qua.program()` block builds; the thing being drawn.
_Avoid_: script, sequence, job

**Program function**:
A user Python function that builds a QUA program and returns it.
_Avoid_: builder, prog

**Acquisition function**:
A user function that builds a QUA program and then runs it on the hardware, so it has no separate program function.
_Avoid_: run function, experiment

**Capture**:
Running user code only until its first QUA program is built, then stopping it before anything else happens.
_Avoid_: intercept, mock run

**Helper**:
A user function called from a program function that emits QUA statements, such as `measure_readout(...)`.
_Avoid_: sub-program, subroutine, macro

**Original program**:
A lab program in `programs/`; read-only.

**Benchmark program**:
A self-contained copy of an original program's QUA-building code, with the same helpers, names and call style.
_Avoid_: fixture, sample program

**Case**:
One benchmark program function together with the sample arguments it is drawn with.

### Diagram

**Diagram**:
The drawn figure. Its horizontal axis is statement order, not time.
_Avoid_: timeline, waveform plot, schedule

**Model**:
The tree of operations, loops, branches and blocks a diagram is drawn from, independent of drawing.
_Avoid_: AST, IR

**Element**:
A named hardware target in QUA (`drive`, `resonator`, `flux_dc`), named exactly as in the code.
_Avoid_: qubit, port

**Line**:
The horizontal line of the diagram for one element.
_Avoid_: channel, wire, lane

**Box**:
The drawing of one `play` or `measure` on a line, labelled with the pulse name and explicit parameters.
_Avoid_: gate

**Icon**:
The symbol at the left of a box, tag or wait naming its instruction (pulse, meter, hourglass, ramp, ...), separated from its values; an instruction with no values shows only its icon.

**Measurement**:
A box for `measure`, drawn in a style distinct from drive boxes.
_Avoid_: readout box

**Explicit parameter**:
A pulse or operation parameter the code sets, such as `amp=0.3`; shown on the diagram.
_Avoid_: override, argument

**Config value**:
A value taken from the hardware configuration because the code did not set it; never shown.
_Avoid_: default

**Barrier**:
The dashed vertical mark for `align` across the aligned lines.

**Tag**:
A small label for a frame or frequency operation (`update_frequency`, `frame_rotation`, …), which does not play a pulse.

**Marker**:
The drawing of a statement with no element (`pause`, `advance_input_stream`) across its region.

### Structure

**Block**:
The drawing of one helper call, labelled with the helper name and the arguments passed at the call site.
_Avoid_: group, subcircuit

**Collapsed block**:
A block drawn as one box that hides its content; the default.

**Expanded block**:
A block drawn as a light region showing its content, still labelled with the call.

**Open region**:
A labelled region whose content is always visible: a QUA scope such as `strict_timing_`, or a helper used as a context manager.
_Avoid_: scope block

**Loop**:
A QUA `for_`, `for_each_` or `while_` and its body.

**Repeat sign**:
The musical repeat bars and dots that open and close a loop on the lines it uses.
_Avoid_: bracket, loop box

**Loop header**:
The text above a loop naming its variable and values, such as `rep in range(0, 2000)`.

**List summary**:
The short form of a long value list: `[first..last] (n)` when evenly spaced, `[first, second, ..., last] (n)` otherwise.
_Avoid_: range (for uneven lists)

**Branch**:
One arm of an `if_` / `elif_` / `else_` or `switch_` / `case_`, labelled with its condition.

### Styling

**Style**:
The single set of every appearance value of a diagram.
_Avoid_: theme, config

**Base size**:
The base font size every style geometry value is a multiple of.
