# Link statements to call stacks by patching `qm-qua`'s private `_get_loc`

To draw helper calls as blocks we must know which helper call emitted each statement. `qm-qua` stamps every statement with a `loc` from `qm._loc._get_loc`, which keeps only the innermost user source line. We replace `_get_loc` in every `qm.*` module for the duration of a trace; the replacement records the full Python call stack (frames, call-site source spans, bound arguments) and appends a trace id to `loc`, so the id travels inside the protobuf and matching is exact. `_ForScope` (no `loc` on `for_` in 1.4.1), `_ElifScope` and `_ProgramScope.__exit__` are patched too. Every patch is restored on every exit path, and a nested trace is refused.

This ties the library to private internals of `qm-qua` 1.4.x: an upgrade starts by rerunning the tests.

## Considered Options

- **Protobuf only**: has no caller information, so blocks are impossible.
- **Static parsing of the user source**: cannot see runtime values such as `**config` contents or element names held in variables.
- **Wrapping the public `qua` functions**: misses names bound with `from qm.qua import play`, and loops and branches are emitted when their `with` block exits, so call order does not match statement order.
