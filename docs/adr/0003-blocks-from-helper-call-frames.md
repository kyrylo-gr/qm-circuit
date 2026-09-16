# Blocks are helper-call frames counted from the frame that entered `qua.program()`

A block is the first user frame below the frame that entered `qua.program()`; consecutive statements sharing that exact frame object form one block. Counting from the program-entering frame, not from the first user frame, keeps the diagram identical when the program function is wrapped in a lambda or another function. Matching the frame object, not the source line, makes two calls from one line (a Python loop) two blocks. Frames inside `qm` are never blocks, so QUA scopes such as `strict_timing_` become open regions. A helper used as a context manager becomes an open region around the caller's statements, because a collapsed block would hide statements the caller wrote.

## Consequences

- Block labels show only the arguments present at the call site (parsed from the call-site source span, `**dict` expanded), with values snapshotted when the helper emits its first statement.
- Lambdas and generator expressions are skipped, so a lambda helper is not grouped into a block.
