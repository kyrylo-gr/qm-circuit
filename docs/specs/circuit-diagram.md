# Spec: circuit diagrams of QUA programs

## Problem Statement

A lab program for a Quantum Machines setup is a Python function that builds a
QUA program. The physicist who wrote it, and colleagues who read it later, want
to see at a glance what the program does on the hardware: which element plays
which pulse, in which order, inside which loop, and with which values set in the
code rather than taken from the configuration.

Today the only views are the Python source and the QUA script that `qm-qua` can
generate. The source mixes program construction with validation, sample
bookkeeping and Python control flow; the generated script flattens every helper
function the user wrote, renames variables to `v1`, `v2`, … and loses the
structure the user designed. Server-side simulation shows waveforms, but it
needs access to a Quantum Machines server, which must not be touched from this
tooling, and waveforms still hide the program's structure.

## Solution

A Python library that takes the function building a QUA program (and its
arguments) and returns a quantum-circuit-style diagram, entirely offline.

- One horizontal line per element, named exactly as in the code.
- One box per pulse or measurement, labelled with the pulse name plus only the
  parameters the code sets explicitly, with their values. Anything from the
  configuration stays hidden.
- Every instruction box starts with an icon for the instruction (pulse, meter,
  hourglass, ramp, ...), then a separator and its values; an instruction with no
  values shows only its icon.
- QUA loops drawn with musical repeat signs, with a readable header such as
  `rep in range(0, 2000)` or `tau_c in [4, 8, 16]`.
- Each call to a user helper function (such as
  `measure_readout(...)`) drawn as one collapsed block, labelled with the
  function name and the arguments passed. An option expands every block to show
  its content.
- Programs built deep inside functions that go on to run a job can be captured:
  the library stops that code right after the program is built.
- No overlapping text, and all appearance settings in one style definition.

## User Stories

1. As a physicist, I want to pass my program-building function and its arguments to one call and get a figure back, so that drawing a program costs one line in a notebook.
2. As a physicist, I want the diagram built without any connection to a Quantum Machines server, so that drawing cannot start, change or disturb an experiment.
3. As a physicist, I want the diagram built without a hardware configuration, so that I can draw programs on any machine with the Python packages installed.
4. As a physicist, I want one horizontal line per element, so that I can see what happens on each channel.
5. As a physicist, I want each line labelled with the element name used in my code, so that the diagram matches the names I think in.
6. As a physicist, I want lines to appear only for elements the program uses, so that the diagram carries no empty channels.
7. As a physicist, I want each played pulse drawn as a box with a pulse icon followed by the pulse name, so that I can recognise the operation.
8. As a physicist, I want measurements drawn in a distinct style from drives, so that I can spot readouts immediately.
9. As a physicist, I want a pulse parameter shown only when I set it in the code, so that the diagram reflects my decisions and not the configuration.
10. As a physicist, I want an explicit amplitude shown with its value (e.g. `amp=0.3`), so that I can check the value used.
11. As a physicist, I want explicit duration, chirp, truncate, condition and target shown with their values, so that every explicit choice is visible.
12. As a physicist, I want a parameter driven by a QUA variable shown with my variable name (e.g. `amp=delta_qm`), so that I can relate it to a sweep.
13. As a physicist, I want chirp rates in human units (e.g. `Hz/s`), so that I can read them without knowing proto field names.
14. As a physicist, I want `wait` shown as an hourglass icon followed by its duration or variable (e.g. `tau_c`), so that I can see idle times.
15. As a physicist, I want consecutive waits merged, so that the diagram stays compact.
16. As a physicist, I want `align` drawn as a dashed barrier across the aligned elements, so that I see where channels are synchronised.
17. As a physicist, I want `align()` and `wait(t)` without elements drawn across all lines, so that global operations look global.
18. As a physicist, I want consecutive aligns merged into one barrier, so that no column is wasted.
19. As a physicist, I want frame and frequency operations (`update_frequency`, `frame_rotation`, `reset_frame`, `ramp_to_zero`, `set_dc_offset`, …) shown as small tags with an icon per operation and their values as written (the icon alone when there are none), so that virtual operations are visible without looking like pulses.
20. As a physicist, I want statements without an element (e.g. `pause`, `advance_input_stream`) drawn as markers across the region, so that nothing the program does silently disappears.
21. As a physicist, I want `for_`, `for_each_` and `while_` loops drawn with musical repeat signs, so that repetition is recognisable at a glance.
22. As a physicist, I want the loop header to show the loop variable and its real values (`rep in range(0, 2000)`), so that I know how many times and over what the loop runs.
23. As a physicist, I want a `for_each_` over several variables shown as tuples (`(tau_c, phi_v) in [(4, 0.1), (8, 0.2)]`), so that I can read which values go together.
24. As a physicist, I want long evenly spaced lists shown as `[first..last] (n)`, so that sweeps stay short.
25. As a physicist, I want long unevenly spaced lists shown as `[first, second, ..., last] (n)`, so that they are short but not mistaken for an even range.
26. As a physicist, I want boolean lists shown as booleans, so that they are not confused with strings.
27. As a physicist, I want repeat signs to span only the lines used inside the loop, with dots on those lines, so that the loop's reach is exact.
28. As a physicist, I want nested loops drawn as nested repeat signs, so that I can follow the nesting order.
29. As a physicist, I want `if_` / `elif_` / `else_` and `switch_` / `case_` drawn as a region split into branches with their conditions, so that conditional parts are visible.
30. As a physicist, I want QUA scopes such as `strict_timing_` drawn as open regions, so that their content stays visible.
31. As a physicist, I want each call to one of my helper functions drawn as a single collapsed block, so that the diagram keeps the structure I designed.
32. As a physicist, I want a collapsed block labelled with the function name and the arguments I passed, with their values, so that I know which variant of the helper runs.
33. As a physicist, I want only the arguments actually passed at the call site shown, not the defaults, so that labels stay short and meaningful.
34. As a physicist, I want `**config` dictionaries unpacked into their keys and values, so that a config-driven call is still readable.
35. As a physicist, I want a keyword argument whose value is a variable of the same name shown only once (`I_val`, not `I_val=I_val`), so that labels are not repetitive.
36. As a physicist, I want QUA variables and streams in labels shown with the name I used at the call site, so that labels do not show internal types or generated names.
37. As a physicist, I want a helper called several times in a Python loop drawn as separate blocks with their own values, so that each call is distinguishable.
38. As a physicist, I want a block to cover only the lines its content uses, joined by a thin connector when those lines are not adjacent, so that it does not seem to act on channels it never touches.
39. As a physicist, I want an option to expand every block, so that I can inspect a helper's pulses when needed.
40. As a physicist, I want an expanded block drawn as a light region labelled with the original call, so that I still see where the helper starts and ends.
41. As a physicist, I want nested helpers collapsed at the first level below my program function, and nested regions when expanded, so that the hierarchy is preserved.
42. As a physicist, I want a helper used as a context manager (`with averaging(...)`) drawn as an open region around my own statements, so that my statements are never hidden inside someone else's block.
43. As a physicist, I want wrapping my program function in a lambda or another function to give the same diagram, so that how I call the library does not change the result.
44. As a physicist, I want to capture the program built inside an acquisition function that would go on to run a job, so that I can draw programs that have no separate builder function.
45. As a physicist, I want capturing to stop my code right after the program is built, so that no job runs and no mocked state is exercised.
46. As a physicist, I want `save` and `assign` hidden by default and shown on request, so that the default diagram focuses on hardware operations.
47. As a physicist, I want empty loops, branches and blocks omitted, so that the diagram contains nothing without content.
48. As a physicist, I want no text to overlap other text, boxes, lines or repeat dots, so that every label is readable.
49. As a physicist, I want long labels wrapped rather than cut, with a sensible cap, so that information is kept without huge boxes.
50. As a physicist, I want a maximum width option that wraps the program into rows, so that long programs fit a page.
51. As a physicist, I want the figure size to follow the content, so that small programs give small figures and large programs are not squeezed.
52. As a physicist, I want the figure returned as a matplotlib figure, so that I can save, embed or adjust it with tools I know.
53. As a physicist, I want an optional title, so that figures are identifiable when saved.
54. As a maintainer, I want every colour, font, line width, spacing and dash pattern in one style definition, so that the look can change without touching layout logic.
55. As a maintainer, I want all sizes relative to one base size, so that scaling the base scales the whole diagram consistently.
56. As a physicist, I want to override the style with a partial set of values, so that I can adapt colours or size for a paper or slide.
57. As a maintainer, I want an intermediate model of the diagram (operations, loops, branches, blocks) separate from the drawing, so that correctness can be tested without pixels.
58. As a maintainer, I want a text dump of that model, so that I can inspect and debug a diagram in a terminal.
59. As a maintainer, I want importing the library to change nothing in `qm`, so that it is safe to import next to real experiment code.
60. As a maintainer, I want every change to `qm` internals undone on every exit path, including exceptions, so that experiment code running afterwards is unaffected.
61. As a maintainer, I want a nested capture refused with a clear error, so that grouping never breaks silently.
62. As a maintainer, I want a benchmark set of self-contained copies of real lab programs, with the same helpers, call style and parameter names as the originals, so that the library is measured against real usage.
63. As a maintainer, I want each benchmark copy to produce the same QUA script as its original, so that the benchmark is faithful.
64. As a maintainer, I want one command that draws every benchmark collapsed and expanded and reports failures and overlaps, so that regressions show up immediately.
65. As a maintainer, I want the original lab programs never modified, so that the benchmark source of truth stays intact.

## Implementation Decisions

**Build offline, never compile.** Entering `qua.program()` is plain Python: the
`qm-qua` DSL functions append statements to an in-memory protobuf AST. No
configuration and no Quantum Machines manager are needed, and element and pulse
names are stored as plain strings. Compilation, simulation and waveform reports
all require the server and are not used.

**Three stages: trace, build, render.** Each stage has one job and a narrow
interface between them.

1. **Tracer.** Runs the user's function and records, for every emitted
   statement, the full Python call stack that produced it.
2. **Model builder.** Walks the protobuf AST into a tree of plain dataclasses
   and uses the recorded stacks to group statements into helper blocks.
3. **Renderer.** Lays the model out and draws it with matplotlib.

**How the tracer links statements to call stacks.** `qm-qua` stamps every
statement with a `loc` string from one internal function, which keeps only the
innermost user source line and therefore cannot tell which helper call emitted
a statement. The tracer replaces that function, in every `qm` module that
imported it, for the duration of a trace. The replacement captures the live
frames (function, line, exact call-site source span, bound arguments) and
returns the original `loc` with a trace id appended. The id travels inside the
protobuf, so matching statements to stacks is exact and independent of call
order. Alternatives rejected:

- Walking the protobuf alone: no caller information.
- Static parsing of the user source alone: cannot see runtime values such as
  `**config` contents or element names held in variables.
- Wrapping the public `qua` functions: misses names bound by
  `from qm.qua import play`, and loops and branches are emitted when their
  `with` block exits, so call order does not match statement order.

Two more internals are patched: `for_` loops receive no `loc` in `qm-qua` 1.4.1,
so the loop scope is patched to fill it; and program-scope exit is hooked so
the traced program is recorded and, in capture mode, the caller is stopped with
a private exception that the capture context swallows. All patches are
restored on every exit path; a nested capture raises an error.

**Which frames count as blocks.** Depth is counted from the frame that entered
`qua.program()`, not from the first user frame, so wrapping the program
function in a lambda or another function changes nothing. The first user frame
below it is a block; consecutive statements sharing that exact frame object form
one block, so two calls from the same source line are two blocks. Frames inside
the `qm` package are never blocks (QUA scopes become open regions). Generator
expressions and lambdas are skipped. A helper used as a context manager becomes
an open region around the caller's statements.

**Explicit versus config parameters.** The protobuf sets optional fields only
when the user passed them, so presence of `amp`, `duration`, `chirp`,
`truncate`, `condition` and target on a play or measure means "explicit".
`* amp(1.0)` written in code is explicit and shown.

**Labels come from values, named by the user.**
- Literals are shown as compact values from the protobuf.
- QUA variables and streams are shown with the Python name used in the program
  function: the tracer maps variable objects to names across frames' locals
  when the program scope exits. Generated names such as `v1` never appear.
- Helper block arguments are the bound argument values snapshotted when the
  helper emits its first statement, restricted to the arguments present at the
  call site (keyword names and positions come from parsing the call-site
  source span; `**dict` is expanded to its keys). When the call cannot be
  matched (e.g. `functools.partial`), all bound arguments are shown.
- Operation names come from the `qm` function actually called, so
  `reset_if_phase` or `frame_rotation` read as written, and their arguments are
  shown as passed.
- Sequences longer than a limit are summarized with their count: evenly spaced
  numbers as `[first..last] (n)`, anything else as `[first, second, ..., last] (n)`.

**Model shape.** Plain dataclasses: a program with its ordered element lines
and body; leaf nodes `Play` (with a measure flag), `Wait`, `Align`, `Op`
(frame/frequency/marker operations); container nodes `Loop` (kind + header),
`If` with `Branch`es, and `Block` (helper function, its parameters, and whether
it is an open scope). A text formatter dumps the tree.

**Layout rules.**
- The x axis is schematic ordering, not time.
- Each item takes horizontal space only on the lines it spans; untouched lines
  are not pushed.
- Items spanning non-adjacent lines are drawn per adjacent group of lines, joined
  by a thin connector.
- Loop headers sit in space reserved above the loop's top line; the gap between
  lines grows only where needed.
- Element-less `align()` and `wait(t)` span every line, and so does any
  container holding one.
- Text widths are measured with the renderer, and the figure size follows the
  content.
- `max_width` wraps top-level statements into rows.
- A box or tag is laid out as icon, separator, text. Icons are line drawings in
  a unit square keyed by the QUA function name; an instruction without an icon
  shows its name as text instead.

**Style.** One style definition holds every appearance value: colours, font
families and weights, line widths, dash patterns, corner rounding, paddings,
gaps, bar and dot sizes, icon and separator sizes, wrap widths, layering.
Geometry is expressed as multiples of the base font size. Callers override with
a style object or a partial mapping merged onto the defaults.

**Public interface.**
- `draw(program_function, *args, expand=False, show_saves=False, title=None, style=None, max_width=None, **kwargs)`
  returns a matplotlib figure.
- `model(program_function, *args, show_saves=False, **kwargs)` returns the model.
- `capture()` is a context manager: code inside it runs until the first
  `qua.program()` exits, then stops. The capture then offers `model()` and
  `draw()` with the same options.

**Benchmark programs.** The user's original lab code is read-only and imports
modules that do not exist in this repository. Self-contained copies of every
program-building function live in a benchmark package, with helpers kept as
helpers, the same names, signatures, call style and module qualification (e.g.
`u.vars_save` stays qualified). Configuration-derived values became literal
constants. Programs built inside acquisition functions were extracted into a
`*_prog` function with the body intact. A cases table gives sample arguments
that build a valid program.

**Pinned dependency.** The tracer depends on private `qm-qua` 1.4.x internals.
A `qm-qua` upgrade starts by rerunning the test suite.

## Testing Decisions

**A good test checks external behaviour through the highest seam.** Tests call
the public interface (`model`, `draw`, `capture`) on small QUA programs and
assert on the model: element lines, which parameters appear with which values,
block labels, loop headers, marker nodes. They never assert on private layout
state or pixels. A test earns its place only if it fails for a named reason; a
bug fix comes with a test that fails on the code before the fix.

**Seams, highest first.**
1. **Model seam**: `model(...)` / `capture().model()`. It covers tracer and
   builder together and holds most assertions.
2. **Figure seam**: `draw(...)` plus the overlap checker, which reads text
   extents, boxes, lines and repeat dots from the drawn figure and reports any
   collision. It covers the "no overlapping text" requirement without pixel
   comparison.
3. **Safety seam**: `qm` internals are identical before import, after a normal
   trace, after an exception inside the program and after a refused nested
   capture.

**Benchmark run.** A script draws every benchmark case collapsed and expanded,
runs the overlap checker on each figure and reports failures. A build check
confirms every benchmark builds offline with only `qm`, `numpy` and the
standard library imported. Figures are reviewed by eye against the benchmark
source and the generated QUA script whenever the renderer changes.

**Prior art.** The existing pytest suite tests the model seam (explicit versus
config parameters, helper labels, loop headers, markers, value formatting,
element-less spans), the capture behaviour, the patch restoration and an
overlap check on a simple program.

## Out of Scope

- Connecting to a Quantum Machines server, compiling, simulating or executing
  programs.
- Real time on the x axis or waveform shapes; the diagram is schematic.
- Validating a program against a hardware configuration.
- Showing values that come from the configuration.
- Stream processing (`stream_processing()` pipelines) in the diagram.
- Modifying the original lab programs.
- Support for `qm-qua` versions other than 1.4.x until the tracer gains a
  fallback.

## Further Notes

Known gaps at the time of writing:
- Expanded diagrams of long programs are very wide; `max_width` must be passed by hand.
- Directly nested loops use one header row each, so deep nests get tall.
- Measure boxes do not show demodulation outputs or streams.
- Lambda helpers are not grouped into blocks.
- Loops that are not a simple `<` comparison fall back to a C-style header.
- Integers of 1000 and up print with underscores.
- Expanded helper labels are capped at six lines, which can hide the last arguments.
- The tracer has no fallback that parses plain `loc` strings when patching fails.
- A branch with nothing drawn is dropped only at the end of an `if` / `switch_`; one followed by a drawn branch stays as an empty region, so the later conditions keep their meaning.

The investigation behind the tracer design, with runnable evidence, is in the
debug folder's investigation report.
