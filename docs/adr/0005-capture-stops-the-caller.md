# `capture()` stops user code with a private exception when the program is built

Many lab programs are built inside acquisition functions that go on to open a Quantum Machine and run a job, so there is no function that only returns the program. `capture()` hooks `_ProgramScope.__exit__`: when the first `qua.program()` block exits, the program is recorded and a private exception unwinds the user's code, and the `capture` context swallows it. Nothing after the program build runs, so no job can start (ADR-0001), and lab code needs no change to be drawn.

## Consequences

- The exception derives from `BaseException`, so a user `except Exception` does not swallow it; `finally` blocks and `with` exits in the user's code still run while it unwinds.
