# Benchmark on self-contained copies of the lab programs, never on the originals

`programs/` holds the user's original lab code and is never modified; it also imports modules that do not exist in this repository, so it cannot be imported here. The benchmark is a package of self-contained copies of every QUA-building function, keeping helpers as helpers, names, signatures, call style and module qualification. Only config-derived values became literal constants, and programs built inside acquisition functions were extracted into a `*_prog` function with the body intact. Structure is what the diagram draws, so a copy that restructures the code would benchmark a different program.

## Consequences

- A change to an original program is not picked up automatically; its copy must be updated by hand.
- Run Python with `-B` so nothing writes `__pycache__` into `programs/`.
