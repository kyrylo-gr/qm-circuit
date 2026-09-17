"""Renderer-independent circuit model of a QUA program (a small dataclass tree)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Play:
    """A ``play`` or ``measure``: one box on the element's line."""

    element: str
    pulse: str
    params: dict[str, str] = field(default_factory=dict)
    """Parameters the code sets explicitly (``amp``, ``duration``, ...), as displayed; config values are absent."""
    measure: bool = False
    """True for ``measure``."""


@dataclass
class Wait:
    """A ``wait``; consecutive waits on the same elements are merged."""

    targets: list[str]
    """Elements waited on; empty = every line."""
    duration: str


@dataclass
class Align:
    """An ``align``, drawn as a dashed barrier."""

    targets: list[str]
    """Aligned elements; empty = every line of the enclosing region."""


@dataclass
class Op:
    """Other instruction: element-bound (update_frequency, ...) or, with no targets, a marker (pause, save)."""

    name: str
    targets: list[str]
    args: str = ""


@dataclass
class Loop:
    """A ``for_``, ``for_each_`` or ``while_`` and its body, drawn between repeat signs."""

    kind: str
    """``"for"``, ``"while"`` or ``"for_each"``."""
    header: str
    """Text above the loop, such as ``rep in range(0, 2000)``."""
    body: list = field(default_factory=list)


@dataclass
class Branch:
    """One arm of an ``if_`` / ``elif_`` / ``else_`` or ``switch_`` / ``case_``."""

    label: str
    """Condition text: ``"if x > 0"``, ``"elif ..."``, ``"else"``."""
    body: list = field(default_factory=list)


@dataclass
class If:
    """An ``if_`` chain or ``switch_``: its branches in order."""

    branches: list[Branch] = field(default_factory=list)


@dataclass
class Block:
    """Statements of one user helper call (collapsible), or a QUA scope such as strict_timing_ (``scope``)."""

    func: str
    """Helper function or scope name."""
    params: list[str]
    """``"k=value"`` for each argument passed at the call site; defaults are left out."""
    body: list = field(default_factory=list)
    scope: bool = False
    """True for an open region (a QUA scope or a helper used as a context manager): always drawn expanded."""


@dataclass
class Program:
    """Root of the model: the program function's name, its element lines and its statements."""

    name: str
    lines: list[str]
    """Element names, one line each, in first-use order."""
    body: list = field(default_factory=list)


def children(node) -> list:
    if isinstance(node, If):
        return [n for b in node.branches for n in b.body]
    return getattr(node, "body", [])


def has_collapsible_block(node) -> bool:
    """True if ``node`` contains a helper-call block, i.e. drawing it with ``expand=True`` shows more."""
    return (isinstance(node, Block) and not node.scope) or any(has_collapsible_block(n) for n in children(node))


def elements(node) -> list[str]:
    """Element names (lines) a node touches, in first-use order."""
    if isinstance(node, Play):
        return [node.element]
    if isinstance(node, (Wait, Align, Op)):
        return list(node.targets)
    out: list[str] = []
    for n in children(node):
        out += [e for e in elements(n) if e not in out]
    return out


def format_model(node, indent: int = 0) -> str:
    """Readable text dump of the model tree.

    Examples:
        >>> print(qm_circuit.format_model(qm_circuit.model(rabi, amplitudes=np.linspace(0, 1.5, 31), n_avg=1000)))
        Program rabi  lines: qubit, resonator
          Loop n in range(0, 1_000)
            Loop a in [0..1.5] (31)
              Play qubit: x180 [amp=a]
              Align qubit, resonator
              Measure resonator: readout
              Wait resonator: 25_000
    """
    pad = "  " * indent
    if isinstance(node, Program):
        head = f"Program {node.name}  lines: {', '.join(node.lines)}"
    elif isinstance(node, Play):
        params = ", ".join(f"{k}={v}" for k, v in node.params.items())
        head = f"{'Measure' if node.measure else 'Play'} {node.element}: {node.pulse}{f' [{params}]' if params else ''}"
    elif isinstance(node, Wait):
        head = f"Wait {', '.join(node.targets) or '(all)'}: {node.duration}"
    elif isinstance(node, Align):
        head = f"Align {', '.join(node.targets) or '(all)'}"
    elif isinstance(node, Op):
        head = f"Op {node.name} {', '.join(node.targets) or '(marker)'}: {node.args}"
    elif isinstance(node, Loop):
        head = f"Loop {node.header}"
    elif isinstance(node, Block):
        head = f"{'Scope' if node.scope else 'Block'} {node.func}({', '.join(node.params)})"
    elif isinstance(node, If):
        out = [pad + "If"]
        for b in node.branches:
            out.append(pad + f"  {b.label}")
            out += [format_model(n, indent + 2) for n in b.body]
        return "\n".join(out)
    else:
        head = repr(node)
    return "\n".join([pad + head, *(format_model(n, indent + 1) for n in children(node))])
