# How it works

qm-circuit never talks to a server. It builds your program with `qm-qua` in the current Python process, watches
that build, and draws the result. This page lists everything it reads and patches, so you can judge what a
`qm-qua` upgrade could break.

The pipeline has three steps: **trace** your function, **build** a model tree, **render** it with matplotlib.

## 1. Trace

While `qm-qua` builds a program, it calls the private function `qm._loc._get_loc()` once per statement and stores
the returned string in the statement's protobuf `loc` field. qm-circuit temporarily replaces that function:

```text
with capture():
    for every imported qm.* module holding _get_loc:
        module._get_loc = record_stack
    run your function

record_stack():
    walk the Python frames (sys._getframe) up to the frame that entered q.program()
    keep "user" frames: named functions (not <lambda>, <genexpr>, ...) in files outside
        qm, qm_circuit, site-packages, dist-packages and the stdlib
    for each new user frame: remember the function name and the arguments passed at its call site
    return "#trace=<n>"          # stored in the protobuf, so each statement carries its call stack
```

Arguments "passed at the call site" come from `inspect.getargvalues` on the frame, plus `ast` on the call
expression (the source line located through `co_positions` and `linecache`). Arguments left at their defaults
therefore stay off the label.

Three more private `qm-qua` classes are patched during the trace:

| Patched | Why |
|---|---|
| `_ForScope._create_statement` | `qm-qua` 1.4.1 leaves `loc` empty on `for_`; the patch copies it in. |
| `_ElifScope.__init__` | `elif_` reuses the `if_`'s `loc`; the patch gives it its own. |
| `_ProgramScope.__enter__` / `__exit__` | Marks the program frame, and stops your code when the program is built. |

!!! note "Where blocks come from"
    A helper becomes a block only if its source file counts as user code. Helpers imported from an installed
    package (inside `site-packages` or `dist-packages`) are not user frames, so their statements are drawn inline.

## 2. Capture stops your code

```text
_ProgramScope.__exit__(exc):
    run the original __exit__
    if the program block ended without an exception and no program is stored yet:
        store the finished program
        raise _Captured          # a BaseException, so `except Exception` in your code cannot swallow it

capture.__exit__(...):
    undo every patch, in reverse order, on every exit path
    swallow _Captured only
```

Code after `with q.program()`, such as opening a Quantum Machine or running a job, never runs. A capture inside
another capture is refused, and if patching fails (for example on an unsupported `qm-qua` version), nothing stays
patched.

## 3. Build the model

The builder walks `program.qua_program.script.body.statements`, the protobuf the program already holds, into
plain dataclasses ([`Play`][qm_circuit.Play], [`Wait`][qm_circuit.Wait], [`Loop`][qm_circuit.Loop],
[`Block`][qm_circuit.Block], …):

```text
group(statements, depth):
    for each statement:
        call = its call stack at depth + 1
        if call is None:                                → convert the statement (play, wait, loop, if, …)
        elif the call also wraps statements it did not emit
             (a helper used as a context manager)       → open region, content always shown
        else                                            → add it to that call's Block
```

- **Explicit parameters:** protobuf `HasField` tells a value the code set, such as `amp=0.3`, from one left to the configuration. Only set values are drawn.
- **Names:** QUA variables are shown with their Python names, found by matching `QuaExpression._expression` objects in the user frames' locals. Expressions are printed with `qm.serialization`'s `ExpressionSerializingVisitor`.

## 4. Render

`render` places the model on a matplotlib figure in inches, measuring text with the Agg renderer so boxes fit their
labels. The figure size follows the content. Every appearance value comes from [`Style`][qm_circuit.Style].

## Compatibility

qm-circuit is pinned to `qm-qua` **1.4.x** because it touches these internals:

- `qm._loc._get_loc`
- `qm.qua._scope_management.scopes._ForScope` (`_create_statement`, `_loc`) and `_ElifScope.__init__`
- `qm.qua._scope_management._core_scopes._ProgramScope` (`__enter__`, `__exit__`, `_program`)
- `qm.qua._expressions.QuaExpression._expression`
- `qm.serialization.expression_serializing_visitor.ExpressionSerializingVisitor`

A `qm-qua` release that renames or reshapes any of these breaks tracing: diagrams fail, but your experiments are
not affected. Supporting a new version starts with running the test suite against it.

The reasoning behind each choice is recorded in the
[architecture decision records](https://github.com/kyrylo-gr/qm-circuit/tree/main/docs/adr).
