# AGENTS.md

## What this is

`qm_circuit` is a Python library that draws a QUA program (Quantum Machines,
`qm-qua`) as a quantum-circuit diagram. A lab program is a Python function that
builds a QUA program; reading its source or the generated QUA script tells you
*what* runs, but not at a glance *where* and *when*. The diagram answers that:
one line per element, named as in the code; one box per pulse, labelled with the
pulse name and only the parameters the code sets explicitly (values coming from
the config stay hidden); QUA loops as musical repeat signs.

The point that makes it more than a waveform plot is **blocks**. Users structure
programs as Python helper functions (`measure_readout(...)`,
`flux_calibration_2p_action(...)`). QUA itself flattens those away, but the
diagram keeps each helper call as one collapsed block labelled with the
arguments passed, and can expand them on request. Everything runs offline: the
library uses the `qm-qua` package to build the program and never talks to a
Quantum Machines server.

## Decisions

**Once the requirement is known, decide alone — the winner is always the
simplest secure code, in the fewest lines.** Multiple ways to build one
unambiguous requirement is not a decision point; it is the ladder below, run
silently, and the answer it gives is the one that ships. Never put "how should
I build this" to the user when what they asked for is already clear.

- **Reach for the pattern the industry already uses** before inventing one.
- **A new dependency has to be the standard answer** to the problem. A library
  already installed that does the job better than code we would write also
  wins. Otherwise, no new library.
- **Build what was asked for and stop.** Extra options, hooks, abstractions and
  detail are scope, not quality. "More complete", "more flexible" and
  "future-proof" are not reasons.
- **Ask yourself the following questions.**
  1. Does this need to exist?   → no: skip it (YAGNI)
  2. Already in this codebase?  → reuse it, don't rewrite
  3. Stdlib does it?            → use it
  4. Native platform feature?   → use it
  5. Installed dependency?      → use it
  6. One line?                  → one line
  7. Only then: the minimum that works

**Most questions are about the requirement.** Ask when the scope itself is the
unknown — whether a use case not yet stated has to be supported, how far
something needs to reach, or two honest readings of the ask would produce
different shapes of code.

**Several ways to build it is not by itself a question.** Run the ladder and
ship the simplest one that is also safe. An implementation question is asked in
two cases only: the ladder does not separate the candidates and which is
simplest is genuinely unclear, or the simplest option is the less secure one and
the trade-off is not ours to settle. Such a question opens by naming why it is
being asked — what makes the call impossible to take alone — and gives each
option's trade-off, not its code.

**A round implements its round's scope and stops there.** Partial is the normal
state: a path that is half built but already useful ships half built. Where a
later round rewrites the code, leave the gap — a fix that the next round deletes
is wasted work and a divergence from the build order. What ships still holds the
target shape, so the gap is a missing branch, never a contradicting one.

**The rule leaves gaps, never remains.** A definition nothing uses is not a
partial path: it is dead code, and the round that stranded it deletes it, in the
same commit. A helper whose last caller was removed, a model node no builder
creates, a `Style` field no renderer reads, a fixture no test asks for, goes with
the change that emptied it.

**A known gap is recorded in the docstring of the function that carries it**, as
a `TODO` naming what misbehaves, why it is not fixed now, and the round that
fixes it. Untracked is the only unacceptable kind. A gap that draws a wrong
diagram silently (a statement missing, on the wrong line or with a wrong value),
leaves `qm` patched after the library returns, or can reach a Quantum Machines
server is not left open — that code does not ship until it is closed.

**A question puts the user in the picture before it asks.** Open with the
motivation — why this is being changed — in words that land for someone who does
not know the internals. Each option then opens with its consequence in plain
language — what changes for the person reading the diagram, for rendering
speed, or for compatibility with `qm-qua` versions, carrying the number where
there is one — before any function name,
type or parameter; a reader with no technical background follows the first line.
Technical detail comes after, exact names and exact terms, each one explained.
Every option also carries what it gives up, what it costs — roughly how many
lines it adds — and what we do instead if it is not chosen. See
[Asking questions](#asking-questions) for how it is delivered.

## Asking questions

Every question to the user — an implementation call from the ladder above or
a `/grilling` session — goes one at a time, never batched. Lead with the
recommended option when the ladder already points to one; options stay
keyboard-selectable, and a typed answer is always offered alongside them.

## Reviews

**Findings follow `## Decisions`.** The recommended option is the one that
leaves the code clearest and smallest; the only findings that add code are a
simplification of what is there or a closed security hole. A finding whose fix
is "add the complex feature" is out of scope unless the change under review
claimed to implement it.

## Stack

Python 3.12, `qm-qua` 1.4.x, matplotlib. No server, no config: building a
program with `with qua.program()` is pure Python and needs neither.

How a diagram is made, in order:

1. **Trace.** `qm-qua` builds a protobuf AST as the user's functions run; each
   statement gets a `loc` string from `qm._loc._get_loc`, holding only the
   innermost user source line. `qm_circuit/tracer.py` patches `_get_loc` in
   every `qm.*` module for the duration of the call and appends a trace id to
   `loc`, keyed to the full Python call stack (frames, `co_positions`, bound
   arguments). It also patches `_ForScope` (no loc on `for_` in 1.4.1), `_ElifScope`
   (elif reuses the if loc) and stops
   the caller when `q.program()` exits, which is what lets `capture()` grab a
   program built inside a function that would go on to run a job. Patches are
   restored on every exit path.
2. **Build.** `qm_circuit/build.py` walks `prog.qua_program` into the plain
   dataclasses of `qm_circuit/nodes.py` (`Play`, `Wait`, `Align`, `Op`, `Loop`,
   `If`, `Block`). Structure, element names and explicit parameters come from
   the proto (`HasField` tells explicit from config); grouping into `Block`s
   comes from the trace (statements sharing one helper-call frame directly below
   the program function); labels use literal values and the caller's variable
   names.
3. **Render.** `qm_circuit/render.py` lays the model out on matplotlib. Every
   appearance value lives in `qm_circuit/style.py` (`Style`), sized relative to
   the base font size; instruction icons are line drawings in
   `qm_circuit/icons.py`, keyed by QUA function name.

The tracer leans on private `qm-qua` internals (`qm._loc`, `_ForScope`,
`_ElifScope`, `_ProgramScope`); a `qm-qua` upgrade starts by rerunning the tests.

Benchmarks: `programs/` holds the user's original lab code and is read-only (it
imports modules that do not exist here). `tests/benchmark_programs/` holds
self-contained copies of every QUA program in it, same structure and helper
calls, with sample arguments in `cases.py`. `debug/` holds exploratory scripts
and figures from the iterations.


## Invariants

Every rule in force, one line each — this is the list to hold in mind when
making a decision, without opening anything. The **argument** behind a rule —
what was rejected, the failure it is written against, the test that enforces it
— is in the linked file. Open that file before changing the code it governs,
because a rule marked *no gate* there has nothing but its own argument stopping
someone "fixing" it.

## Running things

Caveats and the long form: [`docs/code/commands.md`](docs/code/commands.md).

TODO: add commands like "make ..." here with short explanation

**Run Python with `-B`.** Importing from `programs/` would otherwise write
`__pycache__` into the read-only benchmark folder.

**Every tool runs as `python -m <tool>`.** Bare `pytest` and `mypy` resolve to
pipx venvs without this project's dependencies — and still print a version, so a
checkpoint built on them passes while proving nothing.

## Tests

Judged by `.claude/skills/test-quality/SKILL.md`: a test earns its place only if
it fails for a named reason. Boundary trios and both branches on decision logic;
one contract test per public entry point (`draw`, `model`, `capture`).

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues (`kyrylo-gr/qm-circuit`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` + `docs/adr/` at repo root). See `docs/agents/domain.md`.


### Implementing an issue

`/implement` ends with the work sitting uncommitted in the tree. Its review step
is two reviews, in this order, both run before any commit:

1. `/code-review high` — the built-in one, bugs and simplifications, reading the
   working tree as it stands.
2. `/mattpocock-skills:code-review` — Standards and Spec. It has no effort
   level. Give it the branch's merge-base as the fixed point and diff with
   `git diff <merge-base>`, two-dot and no `HEAD`, so the uncommitted work is in
   the diff; its own step 1 assumes everything is committed.

Then report the findings and wait for an explicit OK; only then
`git add`/`git commit` on the current branch. Never push — the remote is
blocked, and issues are updated from the local commit.

Once the commit exists, close the ticket: `gh issue comment <n>` with a one-line
summary of what shipped plus the commit SHA, then `gh issue close <n>`.
